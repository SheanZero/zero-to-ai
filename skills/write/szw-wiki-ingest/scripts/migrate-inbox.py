#!/usr/bin/env python3
"""migrate-inbox.py — 将 inbox/sources/*.md 中 read=true 的项迁移到 resources/。

子命令:
  plan   [--target DIR]                  扫 inbox/sources，输出 to_migrate JSON
  commit [--target DIR]   < <plan.json>  事务性执行：写 resources + 删 inbox

迁移行为（每个 read=true 项）：
  1. 校验 frontmatter 必备字段（type/title/captured/lang）
  2. 规范化文件名：YYYY-MM-DD-<slug>.md
     - 若 inbox 文件名已是该格式则保留
     - 否则用 captured 日期 + title 推导 slug
  3. rewrite markdown 内附件路径：
     ![[../../assets/<slug>/...]]  →  ![[../assets/<slug>/...]]
  4. 写 resources/<new>.md
  5. 删 inbox/sources/<old>.md
  6. 失败回滚：删 resources/<new>.md（inbox 原文件未删）

退出码：
  0  成功（含 dry-run）
  1  非 szw column / 参数错
  2  inbox/sources/ 不存在
  3  存在 frontmatter 严重错误（plan 时输出 warnings；commit 时拒绝）
  4  commit 阶段部分失败（已尽量回滚；详情看 errors）
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from frontmatter import parse_frontmatter, render_frontmatter  # noqa: E402


REQUIRED_FIELDS = ['type', 'title', 'captured', 'lang']

# Inbox-only fields stripped during migration to resources/.
INBOX_ONLY_FIELDS = {'read', 'read_notes'}

# Resource-specific fields filled with defaults when migrating from inbox.
RESOURCE_DEFAULT_FIELDS = {
    'processed': False,
    'wiki_pages': [],
    'summary': '',
}

CANONICAL_RES_FIELDS_HEAD = ['type', 'title', 'source', 'author', 'captured',
                             'lang', 'tags', 'processed', 'wiki_pages',
                             'summary']

# Filename like: 2026-05-07-foo-bar.md
FILENAME_RE = re.compile(r'^(\d{4}-\d{2}-\d{2})-([a-z0-9][a-z0-9-]*)\.md$')

# inbox/sources depth-2 → resources depth-1 (drop one ../)
ASSETS_REWRITE_RE = re.compile(r'!\[\[\.\./\.\./assets/')


def reorder_dict(d: dict, head_order: list) -> dict:
    out = {}
    for k in head_order:
        if k in d:
            out[k] = d[k]
    for k, v in d.items():
        if k not in out:
            out[k] = v
    return out


def transform_inbox_to_resource(content: str) -> str:
    """Strip inbox-only fields, add resource defaults, rewrite asset paths."""
    fm, body = parse_frontmatter(content)
    fm = {k: v for k, v in fm.items() if k not in INBOX_ONLY_FIELDS}
    for k, default in RESOURCE_DEFAULT_FIELDS.items():
        fm.setdefault(k, default)
    fm = reorder_dict(fm, CANONICAL_RES_FIELDS_HEAD)
    body = ASSETS_REWRITE_RE.sub('![[../assets/', body)
    body = body.lstrip('\n')
    return render_frontmatter(fm, '\n\n' + body)


def load_config(target: Path) -> dict:
    cfg_path = target / '.zero' / 'szw-config.json'
    if not cfg_path.exists():
        print(f'ERROR: not an szw Column ({cfg_path} missing)', file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(cfg_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        print(f'ERROR: szw-config.json parse failed: {e}', file=sys.stderr)
        sys.exit(1)


def slugify(text: str, max_len: int = 50) -> str:
    """ASCII slug：lowercase, dash-separated; non-ASCII strips to '' (caller fallbacks)."""
    s = text.strip().lower()
    s = re.sub(r"[^a-z0-9]+", '-', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s[:max_len]


def derive_resource_filename(inbox_filename: str, fm: dict) -> tuple[str, list]:
    """Return (new_filename, warnings)."""
    warnings: list = []
    m = FILENAME_RE.match(inbox_filename)
    if m:
        return inbox_filename, warnings

    captured = str(fm.get('captured', '')).strip()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', captured):
        warnings.append(
            f"captured field invalid or missing: '{captured}'; "
            f"expected YYYY-MM-DD"
        )
    title = str(fm.get('title', '')).strip()
    slug = slugify(title) if title else ''
    if not slug:
        # Fallback to inbox stem (minus extension)
        stem = Path(inbox_filename).stem
        slug = slugify(stem) or 'untitled'
        warnings.append(
            f"could not derive ASCII slug from title; using fallback '{slug}'"
        )
    date_part = captured if re.fullmatch(r'\d{4}-\d{2}-\d{2}', captured) \
        else 'unknown-date'
    return f'{date_part}-{slug}.md', warnings


def collect_asset_rewrites(content: str) -> list:
    """Return list of '![[../../assets/x]] → ![[../assets/x]]' descriptions."""
    out: list = []
    for m in re.finditer(r'!\[\[\.\./\.\./assets/[^\]]+\]\]', content):
        old = m.group(0)
        new = old.replace('![[../../assets/', '![[../assets/', 1)
        out.append(f'{old} → {new}')
    return out


def cmd_plan(args: argparse.Namespace) -> int:
    target = args.target.resolve()
    load_config(target)

    inbox_dir = target / 'inbox' / 'sources'
    if not inbox_dir.is_dir():
        print(f'ERROR: inbox/sources/ not found: {inbox_dir}', file=sys.stderr)
        return 2

    res_dir = target / 'resources'
    existing_resources = (
        {p.name for p in res_dir.glob('*.md')} if res_dir.is_dir() else set()
    )

    to_migrate: list = []
    skipped_read_false: list = []
    files = sorted(inbox_dir.glob('*.md'))

    has_blocking = False
    for f in files:
        if f.name == 'INDEX.md':
            continue
        rel_inbox = f'inbox/sources/{f.name}'
        try:
            content = f.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError) as e:
            to_migrate.append({
                'inbox_path': rel_inbox,
                'frontmatter': {},
                'frontmatter_warnings': [f'read error: {e}'],
                'proposed_resource_path': None,
                'slug_conflict': False,
                'assets_to_rewrite': [],
                'blocking': True,
            })
            has_blocking = True
            continue

        fm, _body = parse_frontmatter(content)
        if not fm.get('read'):
            skipped_read_false.append(rel_inbox)
            continue

        warnings = [f'missing field: {k}' for k in REQUIRED_FIELDS
                    if not fm.get(k)]
        new_name, fn_warnings = derive_resource_filename(f.name, fm)
        warnings.extend(fn_warnings)
        proposed = f'resources/{new_name}'
        slug_conflict = new_name in existing_resources
        blocking = (
            any('missing field' in w for w in warnings)
            or any('captured field invalid' in w for w in warnings)
            or slug_conflict
        )

        to_migrate.append({
            'inbox_path': rel_inbox,
            'frontmatter': fm,
            'frontmatter_warnings': warnings,
            'proposed_resource_path': proposed,
            'slug_conflict': slug_conflict,
            'assets_to_rewrite': collect_asset_rewrites(content),
            'blocking': blocking,
        })
        if blocking:
            has_blocking = True

    out = {
        'to_migrate': to_migrate,
        'skipped_read_false': skipped_read_false,
        'inbox_total_count': len([
            f for f in files if f.name != 'INDEX.md'
        ]),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 3 if has_blocking else 0


def cmd_commit(args: argparse.Namespace) -> int:
    target = args.target.resolve()
    load_config(target)

    inbox_dir = target / 'inbox' / 'sources'
    if not inbox_dir.is_dir():
        print(f'ERROR: inbox/sources/ not found', file=sys.stderr)
        return 2

    raw = sys.stdin.read()
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f'ERROR: stdin JSON parse failed: {e}', file=sys.stderr)
        return 1

    items = plan.get('to_migrate') or []
    if not isinstance(items, list):
        print('ERROR: to_migrate must be a list', file=sys.stderr)
        return 1

    # Pre-flight: any blocking items?
    blocking = [it for it in items if it.get('blocking')]
    if blocking:
        print(
            f'ERROR: {len(blocking)} item(s) blocked; '
            f'fix frontmatter and re-run plan',
            file=sys.stderr,
        )
        return 3

    migrated: list = []
    rolled_back: list = []
    errors: list = []

    res_dir = target / 'resources'
    if not args.dry_run:
        res_dir.mkdir(parents=True, exist_ok=True)

    for it in items:
        inbox_rel = it.get('inbox_path', '')
        proposed = it.get('proposed_resource_path', '')
        if not inbox_rel.startswith('inbox/sources/') or \
           not proposed.startswith('resources/'):
            errors.append({
                'inbox_path': inbox_rel,
                'reason': 'invalid path in plan',
            })
            continue

        inbox_abs = target / inbox_rel
        res_abs = target / proposed

        if not inbox_abs.is_file():
            errors.append({
                'inbox_path': inbox_rel,
                'reason': 'inbox file missing (already migrated?)',
            })
            continue

        if res_abs.exists():
            errors.append({
                'inbox_path': inbox_rel,
                'reason': f'resource already exists: {proposed}',
            })
            continue

        try:
            content = inbox_abs.read_text(encoding='utf-8')
            rewritten = transform_inbox_to_resource(content)
            if args.dry_run:
                migrated.append({
                    'from': inbox_rel,
                    'to': proposed,
                    'asset_rewrites': len(it.get('assets_to_rewrite', [])),
                })
                continue

            # Step 4: write resource
            res_abs.write_text(rewritten, encoding='utf-8')

            # Step 5: delete inbox
            try:
                inbox_abs.unlink()
            except OSError as e:
                # Rollback step 4
                try:
                    res_abs.unlink()
                except OSError:
                    pass
                rolled_back.append(proposed)
                errors.append({
                    'inbox_path': inbox_rel,
                    'reason': f'failed to delete inbox: {e}',
                })
                continue

            migrated.append({
                'from': inbox_rel,
                'to': proposed,
                'asset_rewrites': len(it.get('assets_to_rewrite', [])),
            })
        except (OSError, UnicodeDecodeError) as e:
            # Rollback if resource was written
            if res_abs.exists() and not args.dry_run:
                try:
                    res_abs.unlink()
                    rolled_back.append(proposed)
                except OSError:
                    pass
            errors.append({
                'inbox_path': inbox_rel,
                'reason': str(e),
            })

    out = {
        'migrated': migrated,
        'rolled_back': rolled_back,
        'errors': errors,
        'dry_run': args.dry_run,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))

    return 4 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='cmd', required=True)

    pp = sub.add_parser('plan', help='Scan inbox/sources, output migration plan')
    pp.add_argument('--target', type=Path, default=Path.cwd())

    pc = sub.add_parser('commit',
                        help='Execute migration from stdin plan JSON')
    pc.add_argument('--target', type=Path, default=Path.cwd())
    pc.add_argument('--dry-run', action='store_true')

    args = parser.parse_args()
    if args.cmd == 'plan':
        return cmd_plan(args)
    if args.cmd == 'commit':
        return cmd_commit(args)
    return 1


if __name__ == '__main__':
    sys.exit(main())
