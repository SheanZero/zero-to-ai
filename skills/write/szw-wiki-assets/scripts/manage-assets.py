#!/usr/bin/env python3
"""manage-assets.py — assets/ 目录的孤儿清理 + 远程附件本地化。

子命令:
  orphans  扫所有 .md 找 assets/ 引用，diff 出无引用的文件，列出 / 询问删除
  localize 扫 resources/ 中 markdown 的 http(s) 图片/附件链接，下载到 assets/
           对应 slug 目录，rewrite 成 Obsidian wikilink 本地引用

公用 flags:
  --target DIR   Column 根目录（默认 cwd）
  --no-prompt    禁用所有交互，CI 模式
  --dry-run      不写盘 / 不下载，仅打印将要做的事

orphans 专属:
  --delete       发现孤儿后进入删除流程（TTY 询问每条；非 TTY 需配 --yes）
  --yes          跳过删除确认（与 --delete 配合；危险）
  --include-inbox  也扫 inbox/sources/（默认仅 wiki/ + resources/）

localize 专属:
  --scope SCOPE      处理范围：resources(默认) | wiki | all
  --timeout SECONDS  下载超时（默认 15）
  --skip-cert        允许自签证书（一般不用；urlopen ssl context relax）

退出码:
  0  成功（含 dry-run）
  1  非 szw Column / 参数错
  2  目标 assets/ 不存在
  3  网络下载失败 / 部分失败（localize；详情走 errors）
  4  --delete 但用户取消 / 部分失败
"""

import argparse
import hashlib
import json
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


CONTENT_DIRS_DEFAULT = ('wiki', 'resources')
INBOX_DIR = ('inbox', 'sources')

# Common image/asset extensions (filename sniff fallback when URL has none)
EXT_FROM_MIME = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'image/webp': '.webp',
    'image/svg+xml': '.svg',
    'application/pdf': '.pdf',
    'audio/mpeg': '.mp3',
    'video/mp4': '.mp4',
}

# Markdown / Obsidian image-or-attachment patterns
WIKILINK_RE = re.compile(r'!?\[\[([^\]\n]+)\]\]')          # ![[X]] or [[X]]
MD_IMG_RE = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
MD_LINK_RE = re.compile(r'(?<!!)\[([^\]]*)\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
# HTML media tags (video / audio / source / img with relative src)
HTML_SRC_RE = re.compile(
    r'<(?:video|audio|source|img|track)\s[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)
HTTP_RE = re.compile(r'^https?://', re.IGNORECASE)


# ---------- Column preflight ----------

def load_column(target: Path) -> dict:
    cfg = target / '.zero' / 'szw-config.json'
    if not cfg.exists():
        print(f'ERROR: not an szw Column ({cfg} missing)', file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(cfg.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        print(f'ERROR: szw-config.json parse failed: {e}', file=sys.stderr)
        sys.exit(1)


def is_interactive(no_prompt: bool) -> bool:
    return sys.stdin.isatty() and not no_prompt


def prompt_yes_no(msg: str, default: bool = False) -> bool:
    suffix = '[Y/n]' if default else '[y/N]'
    try:
        v = input(f'{msg} {suffix} ').strip().lower()
    except EOFError:
        return default
    if not v:
        return default
    return v in ('y', 'yes', '1', 'true')


# ---------- Asset reference scanning ----------

def find_asset_refs_in_md(md_path: Path, target: Path,
                          assets_root: Path) -> set[Path]:
    """Find files under assets_root referenced by md_path (resolved abs paths)."""
    refs: set[Path] = set()
    try:
        content = md_path.read_text(encoding='utf-8', errors='ignore')
    except OSError:
        return refs
    md_dir = md_path.parent
    assets_root_str = str(assets_root)

    def _check(link: str) -> None:
        link = link.strip()
        if not link or link.startswith(('#', 'mailto:')):
            return
        if HTTP_RE.match(link):
            return
        # Strip alias / display text from Obsidian wikilink
        link = link.split('|', 1)[0].strip()
        # Strip URL fragment / query
        link = link.split('#', 1)[0]
        link = link.split('?', 1)[0]
        if not link:
            return
        try:
            resolved = (md_dir / link).resolve()
        except (OSError, ValueError):
            return
        if str(resolved).startswith(assets_root_str):
            refs.add(resolved)

    for m in WIKILINK_RE.finditer(content):
        _check(m.group(1))
    for m in MD_IMG_RE.finditer(content):
        _check(m.group(2))
    for m in MD_LINK_RE.finditer(content):
        _check(m.group(2))
    for m in HTML_SRC_RE.finditer(content):
        _check(m.group(1))
    return refs


def scan_md_files(target: Path, scopes: tuple,
                  include_index: bool = True) -> list[Path]:
    """Return list of .md files under requested scope subdirs.

    `include_index=False` skips machine-generated INDEX.md files (used by
    localize/refresh — they regenerate so localize'd content is lost).
    """
    files: list[Path] = []
    for scope in scopes:
        root = target
        for part in scope if isinstance(scope, tuple) else (scope,):
            root = root / part
        if not root.is_dir():
            continue
        for md in root.rglob('*.md'):
            if not include_index and md.name == 'INDEX.md':
                continue
            files.append(md)
    return files


def find_orphan_assets(target: Path, include_inbox: bool
                       ) -> tuple[list[Path], list[Path]]:
    """Return (orphan_files, all_md_scanned)."""
    assets_root = (target / 'assets').resolve()
    if not assets_root.is_dir():
        print(f'ERROR: assets/ not found at {assets_root}', file=sys.stderr)
        sys.exit(2)

    all_assets = {p.resolve() for p in assets_root.rglob('*') if p.is_file()}

    scopes: list = list(CONTENT_DIRS_DEFAULT)
    if include_inbox:
        scopes.append(INBOX_DIR)
    md_files = scan_md_files(target, tuple(scopes))

    referenced: set[Path] = set()
    for md in md_files:
        if '.zero' in md.parts or '.git' in md.parts:
            continue
        referenced.update(find_asset_refs_in_md(md, target, assets_root))

    orphans = sorted(all_assets - referenced)
    return orphans, md_files


# ---------- orphans subcommand ----------

def fmt_size(n: int) -> str:
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024:
            return f'{n:.0f}{unit}' if unit == 'B' else f'{n:.1f}{unit}'
        n /= 1024
    return f'{n:.1f}TB'


def cmd_orphans(args: argparse.Namespace) -> int:
    target = args.target.resolve()
    load_column(target)
    interactive = is_interactive(args.no_prompt)

    orphans, md_files = find_orphan_assets(target, args.include_inbox)

    print(f'Scanned: {len(md_files)} markdown file(s)', file=sys.stderr)
    print(f'Orphan assets found: {len(orphans)}', file=sys.stderr)

    if not orphans:
        print('\n✅ No orphan assets — assets/ is clean.', file=sys.stderr)
        return 0

    total_bytes = 0
    print('\nOrphan assets:', file=sys.stderr)
    rows: list = []
    for p in orphans:
        try:
            size = p.stat().st_size
        except OSError:
            size = 0
        total_bytes += size
        rel = p.relative_to(target.resolve())
        rows.append((rel, size))
        print(f'  - {rel}  ({fmt_size(size)})', file=sys.stderr)
    print(f'\nTotal: {len(orphans)} files, {fmt_size(total_bytes)}',
          file=sys.stderr)

    if not args.delete:
        print('\n(report only; pass --delete to enter deletion flow)',
              file=sys.stderr)
        return 0

    if args.dry_run:
        print('\n(dry-run; would delete the above files)', file=sys.stderr)
        return 0

    # Decide deletion mode
    if args.yes:
        to_delete = [p for p, _ in [(p, _) for p, _ in rows]]
        # Just take all
        to_delete = orphans
    elif interactive:
        print('\n→ Confirm deletions individually (y=delete, n=keep, '
              'a=delete all remaining, q=stop)\n', file=sys.stderr)
        to_delete: list = []
        delete_all = False
        for p in orphans:
            rel = p.relative_to(target.resolve())
            if delete_all:
                to_delete.append(p)
                continue
            try:
                v = input(f'  delete {rel}? [y/N/a/q] ').strip().lower()
            except EOFError:
                break
            if v == 'q':
                break
            if v == 'a':
                delete_all = True
                to_delete.append(p)
            elif v in ('y', 'yes'):
                to_delete.append(p)
    else:
        print('ERROR: --delete in non-interactive mode requires --yes '
              '(safety guard)', file=sys.stderr)
        return 4

    if not to_delete:
        print('\nNothing deleted (user declined all).', file=sys.stderr)
        return 4

    deleted = 0
    deleted_bytes = 0
    errors: list = []
    for p in to_delete:
        try:
            sz = p.stat().st_size
            p.unlink()
            deleted += 1
            deleted_bytes += sz
        except OSError as e:
            errors.append(f'{p}: {e}')

    # Clean up empty parent dirs under assets/
    assets_root = (target / 'assets').resolve()
    for p in sorted({pp.parent for pp in to_delete}, reverse=True):
        try:
            if p == assets_root:
                continue
            if p.is_dir() and not any(p.iterdir()):
                p.rmdir()
        except OSError:
            pass

    print(f'\n✅ Deleted {deleted}/{len(to_delete)} files '
          f'({fmt_size(deleted_bytes)} reclaimed)', file=sys.stderr)
    if errors:
        print(f'⚠️  {len(errors)} delete error(s):', file=sys.stderr)
        for e in errors[:10]:
            print(f'  - {e}', file=sys.stderr)
        return 4

    return 0


# ---------- localize subcommand ----------

_SAFE_NAME_RE = re.compile(r'[^\w.\-]+')


def safe_filename(name: str) -> str:
    name = _SAFE_NAME_RE.sub('-', name).strip('-')
    return name[:80] or 'untitled'


def derive_filename_from_url(url: str) -> tuple[str, str]:
    """Return (basename, ext) extracted from URL path; ext may be ''."""
    parsed = urllib.parse.urlparse(url)
    raw = Path(urllib.parse.unquote(parsed.path)).name
    if not raw or raw == '/':
        return 'remote-' + hashlib.sha256(url.encode()).hexdigest()[:8], ''
    name = safe_filename(raw)
    ext = ''
    if '.' in name:
        stem, dot, ext_raw = name.rpartition('.')
        if 0 < len(ext_raw) <= 8:
            return stem or 'untitled', '.' + ext_raw.lower()
    return name, ext


def download_url(url: str, dst_dir: Path, base_name: str, ext_hint: str,
                 timeout: int, skip_cert: bool, dry_run: bool
                 ) -> Path | None:
    """Download url to dst_dir. Returns final Path on success, None on dry-run/error."""
    ctx = None
    if skip_cert:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    final_name = base_name + ext_hint
    final_path = dst_dir / final_name

    if final_path.exists():
        return final_path  # already downloaded; reuse

    if dry_run:
        return final_path

    req = urllib.request.Request(
        url, headers={'User-Agent': 'szw-wiki-assets/1.0'},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            data = r.read()
            if not ext_hint:
                ct = r.headers.get('Content-Type', '').split(';')[0].strip()
                ext_hint = EXT_FROM_MIME.get(ct, '')
                if ext_hint:
                    final_name = base_name + ext_hint
                    final_path = dst_dir / final_name
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            ssl.SSLError, OSError) as e:
        print(f'  ✗ download failed: {url} → {e}', file=sys.stderr)
        return None

    dst_dir.mkdir(parents=True, exist_ok=True)
    final_path.write_bytes(data)
    return final_path


def localize_one_md(md_path: Path, target: Path, args: argparse.Namespace
                    ) -> dict:
    """Return per-file stats {rewrites, errors}."""
    slug = md_path.stem
    md_rel = md_path.relative_to(target)

    # Compute relative depth from this md to target/assets/
    depth = len(md_rel.parts) - 1  # number of '..' to climb
    rel_prefix = '../' * depth + 'assets/' + slug

    try:
        content = md_path.read_text(encoding='utf-8')
    except OSError as e:
        return {'rewrites': 0, 'errors': [f'read: {e}']}

    rewrites: list = []
    errors: list = []

    def _replace_md_img(m: re.Match) -> str:
        alt = m.group(1)
        url = m.group(2)
        if not HTTP_RE.match(url):
            return m.group(0)  # already local
        base, ext = derive_filename_from_url(url)
        dst_dir = target / 'assets' / slug
        final = download_url(url, dst_dir, base, ext,
                             timeout=args.timeout, skip_cert=args.skip_cert,
                             dry_run=args.dry_run)
        if final is None:
            errors.append(url)
            return m.group(0)
        new_link = f'{rel_prefix}/{final.name}'
        rewrites.append((url, new_link))
        # Use Obsidian wikilink format per CONVENTIONS.md
        return f'![[{new_link}]]'

    new_content = MD_IMG_RE.sub(_replace_md_img, content)

    if rewrites and not args.dry_run:
        try:
            md_path.write_text(new_content, encoding='utf-8')
        except OSError as e:
            errors.append(f'write: {e}')

    return {'rewrites': len(rewrites), 'errors': errors,
            'detail': rewrites}


def cmd_localize(args: argparse.Namespace) -> int:
    target = args.target.resolve()
    load_column(target)

    scope = args.scope
    if scope not in ('resources', 'wiki', 'all'):
        print(f'ERROR: --scope must be resources|wiki|all', file=sys.stderr)
        return 1

    scopes: tuple = (
        ('resources',) if scope == 'resources'
        else ('wiki',) if scope == 'wiki'
        else ('resources', 'wiki')
    )
    md_files = scan_md_files(target, scopes, include_index=False)

    print(f'Scanning {len(md_files)} markdown file(s) under '
          f'{", ".join(s for s in scopes)}/ (skipping INDEX.md)...',
          file=sys.stderr)

    total_rewrites = 0
    total_errors: list = []
    files_changed = 0
    for md in md_files:
        if '.zero' in md.parts or '.git' in md.parts:
            continue
        # Quick scan: skip if no http(s) image at all
        try:
            sample = md.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue
        if not re.search(r'!\[[^\]]*\]\(https?://', sample):
            continue

        rel = md.relative_to(target)
        print(f'\n→ {rel}', file=sys.stderr)
        result = localize_one_md(md, target, args)
        if result['rewrites']:
            files_changed += 1
            total_rewrites += result['rewrites']
            for old, new in result['detail']:
                print(f'  ↓ {old}\n      → {new}', file=sys.stderr)
        if result['errors']:
            total_errors.extend(result['errors'])

    print(
        f'\n{"(dry-run) " if args.dry_run else ""}'
        f'Localized {total_rewrites} link(s) across {files_changed} file(s)',
        file=sys.stderr,
    )
    if total_errors:
        print(f'⚠️  {len(total_errors)} error(s):', file=sys.stderr)
        for e in total_errors[:10]:
            print(f'  - {e}', file=sys.stderr)
        return 3
    return 0


# ---------- refresh subcommand (re-fetch stale URLs via resource source) ----------

# v1: GitHub private user images — JWT expires but image ID (path) is stable;
# re-fetching the source HTML yields a URL with fresh JWT for the same path.
# Other patterns can be added here later (CDN-rebased URLs, etc.).
# Exclude `\` so we don't gobble HTML escape `\"` artifacts when extracting
# fresh URLs from GitHub HTML; markdown-side URLs typically don't have `\`
# either, so the same regex serves both stale-detection and HTML scraping.
STALE_URL_RES = [
    re.compile(
        r'https?://private-user-images\.githubusercontent\.com/'
        r'[^\s)\]"<>\\]+'
    ),
]


def extract_source_from_frontmatter(content: str) -> str | None:
    """Extract `source:` from frontmatter (no PyYAML dep)."""
    m = re.match(r'---\r?\n(.*?)\r?\n---', content, re.DOTALL)
    if not m:
        return None
    for line in m.group(1).split('\n'):
        sm = re.match(r'^\s*source:\s*(.+?)\s*$', line)
        if sm:
            v = sm.group(1).strip().strip('"').strip("'")
            return v or None
    return None


def find_stale_urls(content: str) -> list:
    out: list = []
    for rx in STALE_URL_RES:
        out.extend(rx.findall(content))
    return out


def url_path(url: str) -> str:
    """Path component used as image identity (stable across JWT refresh)."""
    return urllib.parse.urlparse(url).path


def fetch_html(url: str, timeout: int, skip_cert: bool) -> str | None:
    ctx = None
    if skip_cert:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        'User-Agent': (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/'
            '605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
        ),
        'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            data = r.read()
            charset = (r.headers.get_content_charset() or 'utf-8').lower()
            return data.decode(charset, errors='ignore')
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            ssl.SSLError, OSError) as e:
        print(f'  ✗ source fetch failed: {e}', file=sys.stderr)
        return None


def cmd_refresh(args: argparse.Namespace) -> int:
    target = args.target.resolve()
    load_column(target)

    resources_dir = target / 'resources'
    if not resources_dir.is_dir():
        print(f'ERROR: resources/ not found', file=sys.stderr)
        return 2

    # Find affected resources
    affected: list = []
    for md in sorted(resources_dir.glob('*.md')):
        if md.name == 'INDEX.md':
            continue
        try:
            content = md.read_text(encoding='utf-8')
        except OSError:
            continue
        stale = find_stale_urls(content)
        if stale:
            affected.append((md, content, stale))

    print(f'Found {len(affected)} resource(s) with stale URLs to refresh',
          file=sys.stderr)
    if not affected:
        return 0

    import html as _htmlmod
    refreshed_count = 0
    failed_count = 0
    errors: list = []

    for md, content, stale_urls in affected:
        rel = md.relative_to(target)
        slug = md.stem
        print(f'\n→ {rel}  ({len(stale_urls)} stale URL(s))', file=sys.stderr)

        source = extract_source_from_frontmatter(content)
        if not source:
            print('  ✗ no source URL in frontmatter', file=sys.stderr)
            errors.append(f'{rel}: missing source')
            failed_count += len(stale_urls)
            continue

        print(f'  source: {source}', file=sys.stderr)
        html = fetch_html(source, args.timeout, args.skip_cert)
        if html is None:
            errors.append(f'{rel}: source fetch failed')
            failed_count += len(stale_urls)
            continue
        html = _htmlmod.unescape(html)

        # Build path → fresh URL map from new HTML
        fresh_map: dict = {}
        for rx in STALE_URL_RES:
            for u in rx.findall(html):
                pid = url_path(u)
                fresh_map.setdefault(pid, u)
        print(f'  fresh URLs in source: {len(fresh_map)}', file=sys.stderr)

        # Process each stale URL
        new_content = content
        depth = len(rel.parts) - 1
        rel_prefix = '../' * depth + 'assets/' + slug
        dst_dir = target / 'assets' / slug

        for stale in set(stale_urls):  # dedupe
            pid = url_path(stale)
            fresh = fresh_map.get(pid)
            if not fresh:
                print(f'  ✗ no fresh match for path: {pid}', file=sys.stderr)
                errors.append(f'{rel}: no fresh URL for {pid}')
                failed_count += 1
                continue

            local_name = safe_filename(Path(pid).name)
            # Preserve extension
            ext = Path(pid).suffix
            if ext and not local_name.endswith(ext):
                local_name = local_name + ext
            dst = dst_dir / local_name

            if not dst.exists():
                if args.dry_run:
                    print(f'  (dry-run) would download → {local_name}',
                          file=sys.stderr)
                else:
                    final = download_url(
                        fresh, dst_dir, Path(local_name).stem,
                        Path(local_name).suffix or '',
                        timeout=args.timeout, skip_cert=args.skip_cert,
                        dry_run=False,
                    )
                    if final is None:
                        errors.append(f'{rel}: download failed for {pid}')
                        failed_count += 1
                        continue
                    dst = final
            else:
                print(f'  ⏭️  already local: {local_name}', file=sys.stderr)

            # Rewrite by direct string replace — preserves any surrounding
            # syntax (`![alt](URL)`, `[![alt](URL)](URL)`, `<video src="URL">`).
            # This is needed because GitHub README/issue HTML uses many
            # different image/video patterns, not just markdown image.
            local_link = f'{rel_prefix}/{dst.name}'
            n = new_content.count(stale)
            if n > 0:
                new_content = new_content.replace(stale, local_link)
                tag = f' ({n}×)' if n > 1 else ''
                print(f'  ↓ {stale[:60]}...{tag}\n      → {local_link}',
                      file=sys.stderr)
                refreshed_count += n

        if new_content != content and not args.dry_run:
            try:
                md.write_text(new_content, encoding='utf-8')
            except OSError as e:
                errors.append(f'{rel}: write failed: {e}')

    print(
        f'\n{"(dry-run) " if args.dry_run else ""}'
        f'Refreshed {refreshed_count} link(s), failed {failed_count}',
        file=sys.stderr,
    )
    if errors:
        print(f'\n⚠️  {len(errors)} error(s):', file=sys.stderr)
        for e in errors[:15]:
            print(f'  - {e}', file=sys.stderr)
        return 3 if failed_count else 0
    return 0


# ---------- main ----------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='cmd', required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--target', type=Path, default=Path.cwd())
    common.add_argument('--no-prompt', action='store_true')
    common.add_argument('--dry-run', action='store_true')

    p_orph = sub.add_parser('orphans', parents=[common],
                            help='Detect/delete unreferenced assets')
    p_orph.add_argument('--delete', action='store_true',
                        help='Enter deletion flow (default: report only)')
    p_orph.add_argument('--yes', action='store_true',
                        help='Skip per-file confirmation (with --delete)')
    p_orph.add_argument('--include-inbox', action='store_true',
                        help='Also scan inbox/sources/ for refs')

    p_loc = sub.add_parser('localize', parents=[common],
                           help='Download remote http(s) refs to assets/')
    p_loc.add_argument('--scope', default='resources',
                       choices=['resources', 'wiki', 'all'])
    p_loc.add_argument('--timeout', type=int, default=15)
    p_loc.add_argument('--skip-cert', action='store_true',
                       help='Disable TLS cert verification (avoid in prod)')

    p_ref = sub.add_parser('refresh', parents=[common],
                           help='Re-fetch stale URLs (e.g. expired GitHub '
                                'private-user-images JWTs) via the source URL '
                                'in each resource frontmatter')
    p_ref.add_argument('--timeout', type=int, default=20)
    p_ref.add_argument('--skip-cert', action='store_true')

    args = parser.parse_args()
    if args.cmd == 'orphans':
        return cmd_orphans(args)
    if args.cmd == 'localize':
        return cmd_localize(args)
    if args.cmd == 'refresh':
        return cmd_refresh(args)
    return 1


if __name__ == '__main__':
    sys.exit(main())
