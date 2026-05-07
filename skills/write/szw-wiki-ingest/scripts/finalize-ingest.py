#!/usr/bin/env python3
"""finalize-ingest.py — Phase 3：把 AI 决策的 ingest 行动落盘。

子命令:
  commit --resource <rel-path> [--target DIR] [--no-rebuild] [--dry-run]
    stdin 收 ingest plan JSON：
    {
      "summary": "一句话摘要（写入 resource frontmatter）",
      "wiki_actions": [
        {"action": "create", "path": "wiki/concepts/foo.md",
         "frontmatter": {...}, "body": "..."},
        {"action": "update", "path": "wiki/topics/bar.md",
         "patch": {"append_section": "## ...",
                   "append_sources": ["resources/..."],
                   "set_updated": "2026-05-07"}}
      ],
      "log_note": "首次引入 LLM-Wiki 概念"
    }

行为：
  1. 校验 schema 与 wiki_actions 上限
  2. 对 create：渲染 frontmatter + body，写到 wiki/<type>/<slug>.md
     已存在 → 退化为 update（log warn）
  3. 对 update：parse 现有 frontmatter，merge sources / 改 updated；body 追加 section
  4. 改 resource frontmatter：processed=true, wiki_pages, summary
  5. 追加 wiki/log.md
  6. 调用 rebuild-indexes.py（除 --no-rebuild）

退出码：
  0  成功
  1  非 column / wiki 未启用
  2  wiki_actions 超过 ingest_pages_per_source_max
  3  JSON schema 校验失败 / 缺字段
  4  目标 wiki 页路径无效（type 不在 7 类内）
  5  rebuild-indexes 失败（warning，不阻断）
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from frontmatter import parse_frontmatter, render_frontmatter  # noqa: E402


WIKI_TYPES = {'concepts', 'people', 'topics', 'frameworks', 'tools',
              'connections', 'hubs'}

DIR_TO_TYPE = {
    'concepts': 'concept',
    'people': 'person',
    'topics': 'topic',
    'frameworks': 'framework',
    'tools': 'tool',
    'connections': 'connection',
    'hubs': 'hub',
}

CANONICAL_WIKI_FIELDS = ['type', 'title', 'created', 'updated', 'sources',
                         'related', 'status', 'tags', 'derived']


def _attach_body(body: str) -> str:
    """Ensure body has a blank line after frontmatter and trailing newline."""
    body = body.lstrip('\n').rstrip() + '\n'
    return '\n\n' + body

CANONICAL_RES_FIELDS_HEAD = ['type', 'title', 'source', 'author', 'captured',
                             'lang', 'tags', 'processed', 'wiki_pages',
                             'summary']


def load_config(target: Path) -> dict:
    cfg_path = target / '.zero' / 'szw-config.json'
    if not cfg_path.exists():
        print(f'ERROR: not an szw Column ({cfg_path} missing)', file=sys.stderr)
        sys.exit(1)
    try:
        cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        print(f'ERROR: szw-config.json parse failed: {e}', file=sys.stderr)
        sys.exit(1)
    if not cfg.get('wiki', {}).get('enabled'):
        print('ERROR: wiki.enabled=false; run /szw-wiki-init first',
              file=sys.stderr)
        sys.exit(1)
    return cfg


def today() -> str:
    return datetime.now().strftime('%Y-%m-%d')


def reorder_dict(d: dict, head_order: list) -> dict:
    """Return new dict with `head_order` keys first (when present), rest after."""
    out = {}
    for k in head_order:
        if k in d:
            out[k] = d[k]
    for k, v in d.items():
        if k not in out:
            out[k] = v
    return out


def validate_plan(plan: dict, max_pages: int) -> tuple[list, list]:
    """Return (errors, warnings)."""
    errors: list = []
    warnings: list = []
    if not isinstance(plan, dict):
        errors.append('plan must be a JSON object')
        return errors, warnings
    actions = plan.get('wiki_actions')
    if not isinstance(actions, list):
        errors.append('wiki_actions must be a list')
        return errors, warnings
    if len(actions) > max_pages:
        errors.append(
            f'wiki_actions count {len(actions)} exceeds '
            f'ingest_pages_per_source_max ({max_pages})'
        )
    for i, a in enumerate(actions):
        if not isinstance(a, dict):
            errors.append(f'wiki_actions[{i}] must be object')
            continue
        action = a.get('action')
        path = a.get('path', '')
        if action not in ('create', 'update'):
            errors.append(f'wiki_actions[{i}].action must be create|update')
        if not path.startswith('wiki/'):
            errors.append(f'wiki_actions[{i}].path must start with wiki/: {path}')
            continue
        parts = path.split('/')
        if len(parts) != 3 or parts[2] == '' or not parts[2].endswith('.md'):
            errors.append(f'wiki_actions[{i}].path malformed: {path}')
            continue
        if parts[1] not in WIKI_TYPES:
            errors.append(
                f'wiki_actions[{i}].path type "{parts[1]}" not in 7 categories'
            )
        if action == 'create':
            if not isinstance(a.get('frontmatter'), dict):
                errors.append(f'wiki_actions[{i}].frontmatter required for create')
            if not isinstance(a.get('body'), str):
                errors.append(f'wiki_actions[{i}].body (str) required for create')
        if action == 'update':
            if not isinstance(a.get('patch'), dict):
                errors.append(f'wiki_actions[{i}].patch required for update')
    if 'summary' in plan and not isinstance(plan['summary'], str):
        errors.append('summary must be a string')
    return errors, warnings


def normalize_wiki_frontmatter(meta: dict, page_dir: str,
                               resource_rel: str) -> dict:
    """Fill canonical defaults; ensure resource_rel in sources.

    page_dir is the plural directory name (concepts/people/...);
    the singular type field is derived via DIR_TO_TYPE.
    """
    out = dict(meta)
    out.setdefault('type', DIR_TO_TYPE.get(page_dir, page_dir))
    out.setdefault('title', '')
    out.setdefault('created', today())
    out.setdefault('updated', today())
    sources = list(out.get('sources') or [])
    if resource_rel not in sources:
        sources.append(resource_rel)
    out['sources'] = sources
    out.setdefault('related', list(out.get('related') or []))
    out.setdefault('status', 'stub')
    out.setdefault('tags', list(out.get('tags') or []))
    out.setdefault('derived', bool(out.get('derived', False)))
    return reorder_dict(out, CANONICAL_WIKI_FIELDS)


def apply_create(target: Path, action: dict, resource_rel: str,
                 dry_run: bool) -> tuple[str, str]:
    """Create wiki page. Return (status, path)."""
    rel = action['path']
    page_dir = rel.split('/')[1]
    abs_path = target / rel
    if abs_path.exists():
        existing_meta, existing_body = parse_frontmatter(
            abs_path.read_text(encoding='utf-8')
        )
        sources = list(existing_meta.get('sources') or [])
        if resource_rel not in sources:
            sources.append(resource_rel)
        existing_meta['sources'] = sources
        existing_meta['updated'] = today()
        new_body = existing_body
        if action.get('body'):
            new_body = (existing_body.rstrip() + '\n\n'
                        + f"## Added from {resource_rel}\n\n"
                        + action['body'].strip() + '\n')
        if not dry_run:
            content = render_frontmatter(
                reorder_dict(existing_meta, CANONICAL_WIKI_FIELDS),
                _attach_body(new_body),
            )
            abs_path.write_text(content, encoding='utf-8')
        return ('create→update(degraded)', rel)

    fm = normalize_wiki_frontmatter(
        action.get('frontmatter', {}), page_dir, resource_rel
    )
    body = action.get('body', '')
    content = render_frontmatter(fm, _attach_body(body))
    if not dry_run:
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding='utf-8')
    return ('create', rel)


def apply_update(target: Path, action: dict, resource_rel: str,
                 dry_run: bool) -> tuple[str, str]:
    """Update existing wiki page. Return (status, path)."""
    rel = action['path']
    abs_path = target / rel
    patch = action.get('patch') or {}

    if not abs_path.exists():
        page_dir = rel.split('/')[1]
        synth = {
            'action': 'create',
            'path': rel,
            'frontmatter': {
                'type': DIR_TO_TYPE.get(page_dir, page_dir),
                'title': '',
                'status': 'stub',
            },
            'body': patch.get('append_section', '') or '',
        }
        return apply_create(target, synth, resource_rel, dry_run)

    existing_meta, existing_body = parse_frontmatter(
        abs_path.read_text(encoding='utf-8')
    )

    # Update sources
    extra_sources = list(patch.get('append_sources') or [])
    if resource_rel not in extra_sources:
        extra_sources.append(resource_rel)
    sources = list(existing_meta.get('sources') or [])
    for s in extra_sources:
        if s not in sources:
            sources.append(s)
    existing_meta['sources'] = sources

    # Update updated date
    set_updated = patch.get('set_updated') or today()
    existing_meta['updated'] = set_updated

    # Optional related additions
    extra_related = patch.get('append_related') or []
    if extra_related:
        related = list(existing_meta.get('related') or [])
        for r in extra_related:
            if r not in related:
                related.append(r)
        existing_meta['related'] = related

    # Optional status bump
    if patch.get('set_status'):
        existing_meta['status'] = patch['set_status']

    # Optional tag additions
    extra_tags = patch.get('append_tags') or []
    if extra_tags:
        tags = list(existing_meta.get('tags') or [])
        for t in extra_tags:
            if t not in tags:
                tags.append(t)
        existing_meta['tags'] = tags

    # Body: append section if provided
    new_body = existing_body
    section = patch.get('append_section')
    if section:
        new_body = existing_body.rstrip() + '\n\n' + section.strip() + '\n'

    fm = reorder_dict(existing_meta, CANONICAL_WIKI_FIELDS)
    content = render_frontmatter(fm, _attach_body(new_body))
    if not dry_run:
        abs_path.write_text(content, encoding='utf-8')
    return ('update', rel)


def update_resource_frontmatter(target: Path, resource_rel: str,
                                wiki_pages: list, summary: str,
                                dry_run: bool) -> None:
    res_abs = target / resource_rel
    meta, body = parse_frontmatter(res_abs.read_text(encoding='utf-8'))
    meta['processed'] = True
    existing_pages = list(meta.get('wiki_pages') or [])
    for p in wiki_pages:
        if p not in existing_pages:
            existing_pages.append(p)
    meta['wiki_pages'] = existing_pages
    if summary:
        meta['summary'] = summary
    fm = reorder_dict(meta, CANONICAL_RES_FIELDS_HEAD)
    content = render_frontmatter(fm, _attach_body(body))
    if not dry_run:
        res_abs.write_text(content, encoding='utf-8')


def append_log(target: Path, resource_rel: str, results: list,
               summary: str, log_note: str, dry_run: bool) -> None:
    log_path = target / 'wiki' / 'log.md'
    if not log_path.exists() or dry_run:
        return
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    created = [p for s, p in results if s == 'create']
    updated = [p for s, p in results
               if s in ('update', 'create→update(degraded)')]
    lines = [
        f"\n## [{ts}] ingest | {Path(resource_rel).stem}",
        f"- source: {resource_rel}",
        f"- summary: {summary}" if summary else "",
        f"- created ({len(created)}): {', '.join(created) if created else '—'}",
        f"- updated ({len(updated)}): {', '.join(updated) if updated else '—'}",
    ]
    if log_note:
        lines.append(f"- note: {log_note}")
    entry = '\n'.join(l for l in lines if l) + '\n'
    with log_path.open('a', encoding='utf-8') as f:
        f.write(entry)


def trigger_rebuild(target: Path, dry_run: bool) -> int:
    if dry_run:
        return 0
    rebuild_script = Path(__file__).parent / 'rebuild-indexes.py'
    if not rebuild_script.exists():
        return 0
    r = subprocess.run(
        [sys.executable, str(rebuild_script), '--target', str(target)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f'WARN: rebuild-indexes failed (exit {r.returncode}): {r.stderr}',
              file=sys.stderr)
        return 5
    print(r.stdout.strip())
    return 0


def cmd_commit(args: argparse.Namespace) -> int:
    target = args.target.resolve()
    config = load_config(target)
    max_pages = config.get('wiki', {}).get('ingest_pages_per_source_max', 15)

    # Resource sanity
    res_rel = args.resource.lstrip('./')
    res_abs = (target / res_rel).resolve()
    if not res_abs.is_file():
        print(f'ERROR: resource not found: {res_rel}', file=sys.stderr)
        return 1
    try:
        res_abs.relative_to(target / 'resources')
    except ValueError:
        print(f'ERROR: resource must be under resources/: {res_rel}',
              file=sys.stderr)
        return 1

    # Read plan from stdin
    raw = sys.stdin.read()
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f'ERROR: stdin JSON parse failed: {e}', file=sys.stderr)
        return 3

    errors, warnings = validate_plan(plan, max_pages)
    if errors:
        for e in errors:
            print(f'ERROR: {e}', file=sys.stderr)
        # specific exit: count exceeded → 2; type invalid → 4; else → 3
        if any('exceeds' in e for e in errors):
            return 2
        if any('not in 7 categories' in e for e in errors):
            return 4
        return 3
    for w in warnings:
        print(f'WARN: {w}', file=sys.stderr)

    actions = plan.get('wiki_actions', [])
    summary = plan.get('summary', '') or ''
    log_note = plan.get('log_note', '') or ''

    results: list = []
    touched_pages: list = []
    for a in actions:
        if a['action'] == 'create':
            status, rel = apply_create(target, a, res_rel, args.dry_run)
        else:
            status, rel = apply_update(target, a, res_rel, args.dry_run)
        results.append((status, rel))
        if rel not in touched_pages:
            touched_pages.append(rel)

    # Update resource frontmatter
    update_resource_frontmatter(target, res_rel, touched_pages, summary,
                                args.dry_run)

    # Append log
    append_log(target, res_rel, results, summary, log_note, args.dry_run)

    # Rebuild indexes
    rebuild_exit = 0
    if not args.no_rebuild:
        rebuild_exit = trigger_rebuild(target, args.dry_run)

    # Report
    out = {
        'resource': res_rel,
        'wiki_pages': touched_pages,
        'results': [{'status': s, 'path': p} for s, p in results],
        'summary': summary,
        'rebuild_exit': rebuild_exit,
        'dry_run': args.dry_run,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))

    return rebuild_exit  # 0 or 5


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='cmd', required=True)

    pc = sub.add_parser('commit',
                        help='Apply ingest plan from stdin JSON')
    pc.add_argument('--target', type=Path, default=Path.cwd())
    pc.add_argument('--resource', type=str, required=True,
                    help='Relative path to resources/<file>.md')
    pc.add_argument('--no-rebuild', action='store_true')
    pc.add_argument('--dry-run', action='store_true')

    args = parser.parse_args()
    if args.cmd == 'commit':
        return cmd_commit(args)
    return 1


if __name__ == '__main__':
    sys.exit(main())
