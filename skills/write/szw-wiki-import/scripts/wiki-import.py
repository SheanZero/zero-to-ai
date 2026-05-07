#!/usr/bin/env python3
"""
wiki-import.py — 从 vault 1-wiki/ + 4-resources/ 导入到 szw Column wiki/ + resources/。

核心职责:
  1. 扫 vault 与 szw 当前状态（含 SHA256）
  2. 三向 diff（seed-manifest / vault_now / szw_now）
  3. 应用变更：cp + 重写 wikilink + 重写附件路径
  4. 写 .zero/wiki-cache/seed-manifest.json
  5. 触发 rebuild-indexes.py（除 --no-rebuild）

路径映射:
  vault/1-wiki/<type>/<slug>.md      → column/wiki/<type>/<slug>.md
  vault/4-resources/<slug>.md         → column/resources/<slug>.md
  vault/6-assets/<slug>/<file>        → column/assets/<slug>/<file>  (仅 --include-assets)

链接重写:
  [[1-wiki/<type>/<slug>|...]]        → [[wiki/<type>/<slug>|...]]
  [[4-resources/<slug>|...]]          → [[resources/<slug>|...]]
  ![[../6-assets/<slug>/<file>]]      → ![[../assets/<slug>/<file>]]
  ![[../../6-assets/...]]             → ![[../../assets/...]]

冲突处理 (v1):
  默认 keep_szw（保留本地修改）+ 报告
  --force-vault: 强制 vault 覆盖（用于 v2 merge prompt 决策的 apply 阶段）

Usage:
  wiki-import.py [--target DIR] [--vault-path PATH]
                 [--full | --incremental] [--dry-run]
                 [--pages-only] [--include-assets]
                 [--force-vault] [--no-rebuild]

Exit codes:
  0  成功
  1  参数错 / 路径错
  2  非 szw Column / wiki 未启用
  3  vault.path 未配置 / 路径不存在 / 缺 1-wiki+4-resources
  4  conflict detected (incremental 默认；非阻断，保留 szw 本地)
  5  rebuild-indexes 调用失败
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 让 lib 可导入
sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from frontmatter import split_frontmatter  # noqa: E402


WIKI_TYPES = ['concepts', 'people', 'topics', 'frameworks', 'tools', 'connections', 'hubs']


# ---------- Auto-init bridge (calls sibling szw-wiki-init scripts) ----------

def find_wiki_init_scripts() -> Path | None:
    """Locate sibling skill szw-wiki-init/scripts/ via canonical path."""
    canonical = Path(__file__).resolve()
    sibling = canonical.parent.parent.parent / 'szw-wiki-init' / 'scripts'
    if (sibling / 'init-wiki-layer.sh').is_file() and \
       (sibling / 'finalize-wiki-init.py').is_file():
        return sibling
    return None


def bootstrap_wiki_layer(target: Path) -> int:
    """Run init-wiki-layer.sh + finalize-wiki-init.py on target.

    Only forwards --target. No import-side knobs (vault path, bootstrap mode,
    full/incremental, etc.) cross the boundary; init builds an empty skeleton,
    import does the seeding separately.

    Returns 0 on success, non-zero exit code on failure.
    """
    scripts_dir = find_wiki_init_scripts()
    if scripts_dir is None:
        print(
            'ERROR: cannot locate sibling szw-wiki-init/scripts/; '
            'auto-init unavailable. Run /szw-wiki-init manually or pass '
            '--no-auto-init.',
            file=sys.stderr,
        )
        return 6

    print('ℹ️  wiki.enabled is false — auto-bootstrapping via /szw-wiki-init '
          '(empty skeleton)...', file=sys.stderr)

    layer_script = scripts_dir / 'init-wiki-layer.sh'
    r1 = subprocess.run(
        ['bash', str(layer_script), '--target', str(target)],
        capture_output=True, text=True,
    )
    if r1.returncode != 0:
        print(f'ERROR: init-wiki-layer.sh failed (exit {r1.returncode}): '
              f'{r1.stderr}', file=sys.stderr)
        return r1.returncode
    if r1.stdout.strip():
        print(r1.stdout.strip(), file=sys.stderr)

    finalize_script = scripts_dir / 'finalize-wiki-init.py'
    # Only --target forwarded; bootstrap mode defaults to empty-skeleton inside
    # finalize-wiki-init.py. Import knobs intentionally NOT propagated.
    r2 = subprocess.run(
        [sys.executable, str(finalize_script), '--target', str(target)],
        capture_output=True, text=True,
    )
    if r2.returncode != 0:
        print(f'ERROR: finalize-wiki-init.py failed (exit {r2.returncode}): '
              f'{r2.stderr}', file=sys.stderr)
        return r2.returncode
    if r2.stdout.strip():
        print(r2.stdout.strip(), file=sys.stderr)

    print('✅ Auto-init complete; continuing with import...\n', file=sys.stderr)
    return 0


# ---------- Interactive helpers ----------

WIKI_SUBDIR_CANDIDATES = ['1-wiki', '2-wiki', 'wiki', 'Wiki']
RES_SUBDIR_CANDIDATES = ['4-resources', '3-resources', 'resources', 'Resources']
ASSETS_SUBDIR_CANDIDATES = ['6-assets', '5-assets', 'assets', 'Assets']


def is_interactive(no_prompt: bool) -> bool:
    return sys.stdin.isatty() and not no_prompt


def prompt_input(msg: str, default: str | None = None) -> str:
    full = f'{msg} '
    if default is not None and default != '':
        full += f'[{default}] '
    try:
        v = input(full).strip()
    except EOFError:
        return default or ''
    return v or (default or '')


def prompt_yes_no(msg: str, default: bool = False) -> bool:
    suffix = '[Y/n]' if default else '[y/N]'
    v = prompt_input(f'{msg} {suffix}', '').lower()
    if not v:
        return default
    return v in ('y', 'yes', '1', 'true')


def prompt_choice(prompt_msg: str, options: list, default_idx: int = 0) -> str:
    """Show numbered options + accept index OR custom path. Returns chosen string."""
    print(prompt_msg, file=sys.stderr)
    for i, opt in enumerate(options):
        marker = ' *' if i == default_idx else '  '
        print(f'  [{i + 1}]{marker} {opt}', file=sys.stderr)
    v = prompt_input(
        f'Choose [1-{len(options)}, or type other path]',
        str(default_idx + 1),
    )
    if v.isdigit():
        idx = int(v) - 1
        if 0 <= idx < len(options):
            return options[idx]
    return v


def _actual_subdir_case(vault_root: Path, name: str) -> str | None:
    """Return the filesystem-actual case of `name` if it exists as a subdir.

    On case-insensitive filesystems (macOS default), `(vault / 'wiki').is_dir()`
    can match `Wiki/`. We need the actual case so downstream regex rewriters
    match the markdown content correctly.
    """
    target = name.lower()
    try:
        for p in vault_root.iterdir():
            if p.is_dir() and p.name.lower() == target:
                return p.name
    except OSError:
        pass
    return None


def detect_subdirs(vault_root: Path, candidates: list) -> list:
    """Probe candidates → return actual filesystem subdir names (priority-ordered)."""
    matches: list = []
    for c in candidates:
        actual = _actual_subdir_case(vault_root, c)
        if actual and actual not in matches:
            matches.append(actual)
    return matches


def resolve_subdir(vault_root: Path, kind: str, candidates: list,
                   cli_override: str | None, config_default: str | None,
                   interactive: bool, required: bool = True) -> str | None:
    """Pick a subdir by priority: CLI > interactive prompt > auto-detect > config.

    Returns the chosen subdir name (with filesystem-actual case), or None if
    unresolved.
    """
    if cli_override:
        actual = _actual_subdir_case(vault_root, cli_override)
        if actual is None:
            print(f'ERROR: --{kind}-subdir "{cli_override}" not in vault: '
                  f'{vault_root}', file=sys.stderr)
            return None
        return actual

    matches = detect_subdirs(vault_root, candidates)

    if interactive:
        if matches:
            chosen = prompt_choice(
                f'\n{kind} dir candidates in vault {vault_root}:',
                matches,
                default_idx=0,
            )
            if chosen not in matches:
                actual = _actual_subdir_case(vault_root, chosen)
                if actual is None:
                    print(f'ERROR: "{chosen}" not in vault', file=sys.stderr)
                    return None
                return actual
            return chosen
        v = prompt_input(
            f'\nNo {kind} dir auto-detected in vault.\n'
            f'  Enter {kind} subdir (relative to vault), or empty to skip',
            ''
        )
        if v:
            actual = _actual_subdir_case(vault_root, v)
            if actual:
                return actual
        return None

    # Non-interactive
    if matches:
        if matches[0] != config_default:
            print(f'ℹ️  detected {kind} subdir: {matches[0]} '
                  f'(config default was {config_default})', file=sys.stderr)
        return matches[0]
    if config_default:
        actual = _actual_subdir_case(vault_root, config_default)
        if actual:
            return actual
    if required:
        print(f'ERROR: no {kind} subdir found; tried {candidates} '
              f'and config default {config_default}', file=sys.stderr)
    return None


def resolve_assets_inclusion(vault_root: Path, assets_subdir: str | None,
                             cli_include: bool, interactive: bool
                             ) -> tuple[bool, str | None]:
    """Decide whether to include assets. Returns (include, subdir_or_None)."""
    if cli_include:
        return True, assets_subdir

    if not assets_subdir:
        return False, None
    assets_dir = vault_root / assets_subdir
    if not assets_dir.is_dir():
        return False, None

    if not interactive:
        return False, assets_subdir

    # Compute size + count for prompt
    n_files = 0
    n_bytes = 0
    for f in assets_dir.rglob('*'):
        if f.is_file():
            n_files += 1
            try:
                n_bytes += f.stat().st_size
            except OSError:
                pass
    size_mb = n_bytes / (1024 * 1024)
    print(f'\n📦 Found assets: {assets_subdir}/ '
          f'({n_files} files, {size_mb:.1f} MB)', file=sys.stderr)
    include = prompt_yes_no('Include assets in import?', default=False)
    return include, assets_subdir


# ---------- 链接重写 ----------

# Module-level config: subdir names. Set in main() based on CLI/config/probe.
_VAULT_SUBDIRS = {
    'wiki': '1-wiki',
    'resources': '4-resources',
    'assets': '6-assets',
}
_REWRITERS: dict = {}


def _build_rewriters() -> None:
    """Compile regex patterns from current _VAULT_SUBDIRS into _REWRITERS."""
    w = re.escape(_VAULT_SUBDIRS['wiki'])
    r = re.escape(_VAULT_SUBDIRS['resources'])
    a = re.escape(_VAULT_SUBDIRS['assets'])
    _REWRITERS['wiki_link'] = re.compile(rf'\[\[{w}/')
    _REWRITERS['res_link'] = re.compile(rf'\[\[{r}/')
    _REWRITERS['assets_path'] = re.compile(rf'(\.\./)+{a}/')
    _REWRITERS['fm_wiki'] = re.compile(rf'(?<![\w/-]){w}/')
    _REWRITERS['fm_res'] = re.compile(rf'(?<![\w/-]){r}/')


def configure_subdirs(wiki_subdir: str, resources_subdir: str,
                      assets_subdir: str) -> None:
    """Set the vault subdir names + recompile rewriters."""
    _VAULT_SUBDIRS['wiki'] = wiki_subdir
    _VAULT_SUBDIRS['resources'] = resources_subdir
    _VAULT_SUBDIRS['assets'] = assets_subdir
    _build_rewriters()


_build_rewriters()  # initial defaults


def _rewrite_body(body: str) -> str:
    """Rewrite wikilinks and asset paths in markdown body."""
    body = _REWRITERS['wiki_link'].sub('[[wiki/', body)
    body = _REWRITERS['res_link'].sub('[[resources/', body)

    assets_subdir = _VAULT_SUBDIRS['assets']

    def _asset_repl(m):
        depth_prefix = m.group(0).replace(f'{assets_subdir}/', '')
        return depth_prefix + 'assets/'

    body = _REWRITERS['assets_path'].sub(_asset_repl, body)
    return body


def _rewrite_frontmatter(fm_str: str) -> str:
    """Rewrite vault path prefixes in frontmatter (sources/related/wiki_pages 等)."""
    fm_str = _REWRITERS['fm_wiki'].sub('wiki/', fm_str)
    fm_str = _REWRITERS['fm_res'].sub('resources/', fm_str)
    return fm_str


def rewrite_links(content: str) -> str:
    """Rewrite vault-style paths to szw-style in both frontmatter and body."""
    fm_str, body = split_frontmatter(content)
    body = _rewrite_body(body)
    if fm_str:
        fm_str = _rewrite_frontmatter(fm_str)
        return f'---\n{fm_str}\n---\n{body.lstrip(chr(10))}'
    return body


# ---------- 文件扫描 ----------

def list_vault_files(vault_root: Path, wiki_subdir: str = '1-wiki',
                     resources_subdir: str = '4-resources',
                     pages_only: bool = False):
    """List all importable vault files. Returns dict: rel_path -> abs_path.

    rel_path uses vault-side prefix (1-wiki/... or 4-resources/...).
    """
    files = {}
    wiki_root = vault_root / wiki_subdir
    if wiki_root.is_dir():
        for type_name in WIKI_TYPES:
            type_dir = wiki_root / type_name
            if not type_dir.is_dir():
                continue
            for f in type_dir.glob('*.md'):
                # Skip INDEX.md (vault may have its own)
                if f.name == 'INDEX.md':
                    continue
                rel = f.relative_to(vault_root)
                files[str(rel)] = f
        # vault root index.md doesn't go to wiki INDEX.md (we rebuild ours)

    if not pages_only:
        res_root = vault_root / resources_subdir
        if res_root.is_dir():
            for f in res_root.glob('*.md'):
                rel = f.relative_to(vault_root)
                files[str(rel)] = f

    return files


def list_szw_files(szw_root: Path, pages_only: bool = False):
    """List szw current state. Returns dict: szw_rel_path -> abs_path.

    szw_rel_path is column-side (wiki/<type>/<slug>.md, resources/<slug>.md).
    """
    files = {}
    wiki_root = szw_root / 'wiki'
    if wiki_root.is_dir():
        for type_name in WIKI_TYPES:
            type_dir = wiki_root / type_name
            if not type_dir.is_dir():
                continue
            for f in type_dir.glob('*.md'):
                if f.name == 'INDEX.md':
                    continue
                rel = f.relative_to(szw_root)
                files[str(rel)] = f

    if not pages_only:
        res_root = szw_root / 'resources'
        if res_root.is_dir():
            for f in res_root.glob('*.md'):
                if f.name == 'INDEX.md':
                    continue
                rel = f.relative_to(szw_root)
                files[str(rel)] = f

    return files


# ---------- 路径映射 ----------

def vault_to_szw_path(vault_rel: str) -> str:
    """Map vault-side rel path → szw-side rel path (uses configured subdirs)."""
    w = _VAULT_SUBDIRS['wiki'] + '/'
    r = _VAULT_SUBDIRS['resources'] + '/'
    if vault_rel.startswith(w):
        return 'wiki/' + vault_rel[len(w):]
    if vault_rel.startswith(r):
        return 'resources/' + vault_rel[len(r):]
    raise ValueError(f'unmappable vault path: {vault_rel}')


# ---------- Hash ----------

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_text(path.read_text(encoding='utf-8'))


# ---------- Manifest ----------

def load_seed_manifest(cache_dir: Path) -> dict:
    """Load .zero/wiki-cache/seed-manifest.json. Returns {} if missing."""
    path = cache_dir / 'seed-manifest.json'
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        return {}


def save_seed_manifest(cache_dir: Path, manifest: dict, dry_run: bool):
    if dry_run:
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / 'seed-manifest.json'
    path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + '\n',
        encoding='utf-8'
    )


# ---------- Apply ----------

def import_one(vault_abs: Path, szw_abs: Path, dry_run: bool):
    """Read vault file, rewrite links, write to szw. Returns rewritten_content (always)."""
    content = vault_abs.read_text(encoding='utf-8')
    rewritten = rewrite_links(content)
    if not dry_run:
        szw_abs.parent.mkdir(parents=True, exist_ok=True)
        szw_abs.write_text(rewritten, encoding='utf-8')
    return rewritten


def import_assets(vault_root: Path, szw_root: Path, dry_run: bool):
    """Copy vault assets subdir → szw/assets/. Returns (copied_files, copied_bytes)."""
    src = vault_root / _VAULT_SUBDIRS['assets']
    dst = szw_root / 'assets'
    if not src.is_dir():
        return 0, 0

    copied_files = 0
    copied_bytes = 0
    for f in src.rglob('*'):
        if f.is_file():
            rel = f.relative_to(src)
            target = dst / rel
            if dry_run:
                copied_files += 1
                copied_bytes += f.stat().st_size
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, target)
            copied_files += 1
            copied_bytes += f.stat().st_size

    return copied_files, copied_bytes


# ---------- Three-way diff ----------

def compute_actions(vault_files, szw_files, seed_manifest, mode='incremental',
                    force_vault=False):
    """Decide what to do for each file.

    Returns list of action dicts:
      {action: 'add' | 'fast-forward' | 'skip' | 'conflict' | 'vault-deleted', ...}
    """
    actions = []
    seen_szw = set()

    for vault_rel, vault_abs in sorted(vault_files.items()):
        # Compute vault-now-hash AFTER rewrite (because that's what would be written)
        rewritten = rewrite_links(vault_abs.read_text(encoding='utf-8'))
        vault_now = sha256_text(rewritten)

        szw_rel = vault_to_szw_path(vault_rel)
        szw_abs = szw_files.get(szw_rel)
        szw_now = sha256_file(szw_abs) if szw_abs and szw_abs.exists() else None
        if szw_abs:
            seen_szw.add(szw_rel)

        seed_hash = seed_manifest.get(vault_rel)

        action = {
            'vault_rel': vault_rel,
            'szw_rel': szw_rel,
            'vault_now_hash': vault_now,
            'szw_now_hash': szw_now,
            'seed_hash': seed_hash,
        }

        if mode == 'full':
            # Force vault → szw (no conflict prompt)
            action['action'] = 'force-write'
            actions.append(action)
            continue

        # Incremental logic
        if szw_abs is None:
            action['action'] = 'add'
        elif szw_now == vault_now:
            # already in sync; just refresh manifest if stale
            action['action'] = 'skip-equal'
        elif seed_hash is None:
            # Never seeded; szw exists; treat as "first-time" — use force-vault if set, else conflict
            action['action'] = 'force-write' if force_vault else 'conflict-no-seed'
        elif szw_now == seed_hash:
            # szw unchanged since seed; vault has updates
            action['action'] = 'fast-forward'
        elif vault_now == seed_hash:
            # vault unchanged since seed; szw has local changes (kept)
            action['action'] = 'skip-szw-edited'
        else:
            # both changed
            action['action'] = 'force-write' if force_vault else 'conflict'

        actions.append(action)

    # vault-deleted: szw has files not present in vault now
    for szw_rel, szw_abs in szw_files.items():
        if szw_rel in seen_szw:
            continue
        # check if seed_manifest had it (vault-side rel)
        # need reverse mapping: szw_rel → possible vault_rel
        if szw_rel.startswith('wiki/'):
            vault_rel_candidate = (
                _VAULT_SUBDIRS['wiki'] + '/' + szw_rel[len('wiki/'):]
            )
        elif szw_rel.startswith('resources/'):
            vault_rel_candidate = (
                _VAULT_SUBDIRS['resources'] + '/' + szw_rel[len('resources/'):]
            )
        else:
            continue

        if vault_rel_candidate in seed_manifest:
            # was seeded but vault deleted it
            actions.append({
                'action': 'vault-deleted',
                'szw_rel': szw_rel,
                'vault_rel': vault_rel_candidate,
                'seed_hash': seed_manifest[vault_rel_candidate],
            })
        # else: szw-only file (never seeded; column-local) → ignore

    return actions


# ---------- Main ----------

def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--target', type=Path, default=Path.cwd())
    parser.add_argument('--vault-path', type=Path,
                        help='Override vault.path from local config')
    parser.add_argument('--full', action='store_true',
                        help='Full vault → szw overwrite; ignore szw local changes')
    parser.add_argument('--incremental', action='store_true',
                        help='Default; three-way diff + conflict report')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print plan, do not write')
    parser.add_argument('--pages-only', action='store_true',
                        help='Skip 4-resources/ (only import 1-wiki/)')
    parser.add_argument('--include-assets', action='store_true',
                        help='Copy vault/6-assets/ → column/assets/')
    parser.add_argument('--force-vault', action='store_true',
                        help='In conflicts, take vault (use only after merge decision)')
    parser.add_argument('--no-rebuild', action='store_true',
                        help='Skip calling rebuild-indexes.py at the end')
    parser.add_argument('--no-auto-init', action='store_true',
                        help='Disable auto-bootstrapping wiki layer when '
                             'wiki.enabled is false (default: auto-init ON)')
    parser.add_argument('--no-prompt', action='store_true',
                        help='Disable interactive prompts (CI mode); rely on '
                             'flags + config + auto-detect defaults')
    parser.add_argument('--wiki-subdir', type=str,
                        help=f'Override vault wiki subdir (probes '
                             f'{WIKI_SUBDIR_CANDIDATES} when omitted)')
    parser.add_argument('--resources-subdir', type=str,
                        help=f'Override vault resources subdir (probes '
                             f'{RES_SUBDIR_CANDIDATES} when omitted)')
    parser.add_argument('--assets-subdir', type=str,
                        help=f'Override vault assets subdir (probes '
                             f'{ASSETS_SUBDIR_CANDIDATES} when omitted)')
    args = parser.parse_args()

    target = args.target.resolve()
    interactive = is_interactive(args.no_prompt)

    # Preflight
    config_path = target / '.zero' / 'szw-config.json'
    if not config_path.exists():
        print(f'ERROR: not an szw Column ({config_path} missing)', file=sys.stderr)
        sys.exit(2)

    try:
        config = json.loads(config_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        print(f'ERROR: szw-config.json parse failed: {e}', file=sys.stderr)
        sys.exit(2)

    if not config.get('wiki', {}).get('enabled'):
        if args.no_auto_init:
            print('ERROR: wiki.enabled=false; run /szw-wiki-init first '
                  '(or drop --no-auto-init)', file=sys.stderr)
            sys.exit(2)
        rc = bootstrap_wiki_layer(target)
        if rc != 0:
            sys.exit(rc)
        # Re-load config after bootstrap
        config = json.loads(config_path.read_text(encoding='utf-8'))
        if not config.get('wiki', {}).get('enabled'):
            print('ERROR: wiki.enabled still false after auto-init',
                  file=sys.stderr)
            sys.exit(2)

    # Resolve vault.path: --vault-path > local config > interactive prompt
    vault_root = None
    if args.vault_path:
        vault_root = args.vault_path.resolve()
    else:
        local_path = target / '.zero' / 'szw-config.local.json'
        if local_path.exists():
            try:
                local = json.loads(local_path.read_text(encoding='utf-8'))
            except json.JSONDecodeError as e:
                print(f'ERROR: szw-config.local.json parse failed: {e}',
                      file=sys.stderr)
                sys.exit(3)
            vp = local.get('vault', {}).get('path')
            if vp:
                vault_root = Path(vp).resolve()

    if vault_root is None:
        if interactive:
            print('\nℹ️  Vault path not given via --vault-path or '
                  '.zero/szw-config.local.json.', file=sys.stderr)
            v = prompt_input('Enter vault path (absolute)', '')
            v = v.strip().strip('"').strip("'")
            if not v:
                print('ERROR: no vault path provided', file=sys.stderr)
                sys.exit(3)
            vault_root = Path(v).expanduser().resolve()
        else:
            print('ERROR: vault.path not configured; pass --vault-path or '
                  'set in .zero/szw-config.local.json '
                  '(or drop --no-prompt to be asked interactively)',
                  file=sys.stderr)
            sys.exit(3)

    if not vault_root.is_dir():
        print(f'ERROR: vault path not a directory: {vault_root}', file=sys.stderr)
        sys.exit(3)

    # Resolve subdirs: CLI > interactive prompt > probe > config default
    vault_cfg = config.get('vault', {})

    wiki_subdir = resolve_subdir(
        vault_root, 'wiki', WIKI_SUBDIR_CANDIDATES,
        cli_override=args.wiki_subdir,
        config_default=vault_cfg.get('wiki_subdir', '1-wiki'),
        interactive=interactive,
        required=True,
    )
    if not wiki_subdir:
        sys.exit(3)

    resources_subdir = None
    if not args.pages_only:
        resources_subdir = resolve_subdir(
            vault_root, 'resources', RES_SUBDIR_CANDIDATES,
            cli_override=args.resources_subdir,
            config_default=vault_cfg.get('resources_subdir', '4-resources'),
            interactive=interactive,
            required=True,
        )
        if not resources_subdir:
            sys.exit(3)

    assets_subdir = None
    if args.assets_subdir:
        assets_subdir = _actual_subdir_case(vault_root, args.assets_subdir)
    else:
        matches = detect_subdirs(vault_root, ASSETS_SUBDIR_CANDIDATES)
        assets_subdir = matches[0] if matches else None

    # Decide assets inclusion (interactive prompts > --include-assets flag)
    include_assets, _ = resolve_assets_inclusion(
        vault_root, assets_subdir,
        cli_include=args.include_assets,
        interactive=interactive,
    )

    # Apply resolved subdirs to module-level rewriters
    configure_subdirs(
        wiki_subdir,
        resources_subdir or vault_cfg.get('resources_subdir', '4-resources'),
        assets_subdir or '6-assets',
    )

    mode = 'full' if args.full else 'incremental'

    # Scan
    vault_files = list_vault_files(vault_root, wiki_subdir, resources_subdir,
                                   pages_only=args.pages_only)
    szw_files = list_szw_files(target, pages_only=args.pages_only)

    cache_dir = target / '.zero' / 'wiki-cache'
    seed_manifest = load_seed_manifest(cache_dir)

    actions = compute_actions(vault_files, szw_files, seed_manifest,
                              mode=mode, force_vault=args.force_vault)

    # Apply
    counters = {
        'added': 0, 'fast-forwarded': 0, 'force-written': 0,
        'skipped-equal': 0, 'skipped-szw-edited': 0,
        'conflicts': 0, 'vault-deleted': 0,
    }
    conflict_details = []

    for action in actions:
        a = action['action']
        szw_rel = action['szw_rel']
        szw_abs = target / szw_rel

        if a == 'add':
            vault_abs = vault_files[action['vault_rel']]
            import_one(vault_abs, szw_abs, args.dry_run)
            seed_manifest[action['vault_rel']] = action['vault_now_hash']
            counters['added'] += 1
        elif a == 'fast-forward':
            vault_abs = vault_files[action['vault_rel']]
            import_one(vault_abs, szw_abs, args.dry_run)
            seed_manifest[action['vault_rel']] = action['vault_now_hash']
            counters['fast-forwarded'] += 1
        elif a == 'force-write':
            vault_abs = vault_files[action['vault_rel']]
            import_one(vault_abs, szw_abs, args.dry_run)
            seed_manifest[action['vault_rel']] = action['vault_now_hash']
            counters['force-written'] += 1
        elif a == 'skip-equal':
            seed_manifest[action['vault_rel']] = action['vault_now_hash']
            counters['skipped-equal'] += 1
        elif a == 'skip-szw-edited':
            counters['skipped-szw-edited'] += 1
        elif a == 'conflict':
            counters['conflicts'] += 1
            conflict_details.append({
                'szw_rel': szw_rel,
                'vault_rel': action['vault_rel'],
                'seed_hash': action['seed_hash'][:12] if action['seed_hash'] else None,
                'vault_now': action['vault_now_hash'][:12],
                'szw_now': action['szw_now_hash'][:12],
            })
        elif a == 'conflict-no-seed':
            counters['conflicts'] += 1
            conflict_details.append({
                'szw_rel': szw_rel,
                'vault_rel': action['vault_rel'],
                'reason': 'first-import-but-szw-exists',
                'vault_now': action['vault_now_hash'][:12],
                'szw_now': action['szw_now_hash'][:12],
            })
        elif a == 'vault-deleted':
            counters['vault-deleted'] += 1

    # Save manifest
    save_seed_manifest(cache_dir, seed_manifest, args.dry_run)

    # Assets
    asset_files, asset_bytes = (0, 0)
    if include_assets:
        asset_files, asset_bytes = import_assets(vault_root, target, args.dry_run)

    # Report
    print(f"\n{'(dry-run) ' if args.dry_run else ''}Wiki import done at: {target}")
    print(f"Vault: {vault_root}")
    print(f"Mode: {mode}{' (force-vault)' if args.force_vault else ''}")
    print(f"\nResults:")
    print(f"  added:              {counters['added']}")
    print(f"  fast-forwarded:     {counters['fast-forwarded']}")
    if counters['force-written']:
        print(f"  force-written:      {counters['force-written']}")
    print(f"  skipped (equal):    {counters['skipped-equal']}")
    print(f"  skipped (szw-edit): {counters['skipped-szw-edited']}")
    print(f"  conflicts:          {counters['conflicts']}")
    print(f"  vault-deleted:      {counters['vault-deleted']}")
    if include_assets:
        print(f"  assets copied:      {asset_files} files, {asset_bytes // 1024} KB")

    if conflict_details:
        print(f"\n⚠️  {len(conflict_details)} conflict(s) — szw local kept (default keep_szw):")
        for c in conflict_details[:10]:
            print(f"  - {c['szw_rel']}")
        if len(conflict_details) > 10:
            print(f"  ... and {len(conflict_details) - 10} more")
        print(f"\n  Resolve options:")
        print(f"    1) Edit szw locally to match desired state")
        print(f"    2) /szw-wiki-import --force-vault  (overwrite all conflicts with vault)")
        print(f"    3) [v2] /szw-wiki-import --merge-prompt  (interactive resolution)")

    # Trigger rebuild
    if not args.no_rebuild and not args.dry_run and (
        counters['added'] + counters['fast-forwarded'] + counters['force-written']
    ) > 0:
        rebuild_script = Path(__file__).parent / 'rebuild-indexes.py'
        if rebuild_script.exists():
            print(f"\n→ Running rebuild-indexes.py...")
            r = subprocess.run([sys.executable, str(rebuild_script),
                                '--target', str(target)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                print(f"WARN: rebuild-indexes failed (exit {r.returncode}): {r.stderr}",
                      file=sys.stderr)
                # not fatal
            else:
                print(r.stdout.strip())

    # Append to wiki/log.md
    if not args.dry_run and (counters['added'] + counters['fast-forwarded'] +
                             counters['force-written']) > 0:
        log_path = target / 'wiki' / 'log.md'
        if log_path.exists():
            ts = datetime.now().strftime('%Y-%m-%d %H:%M')
            n_changed = (counters['added'] + counters['fast-forwarded'] +
                         counters['force-written'])
            log_entry = (
                f"\n## [{ts}] import | from vault\n"
                f"- mode: {mode}\n"
                f"- vault: {vault_root}\n"
                f"- changed: {n_changed} (added={counters['added']}, "
                f"ff={counters['fast-forwarded']}, "
                f"force={counters['force-written']})\n"
                f"- conflicts: {counters['conflicts']}\n"
            )
            with log_path.open('a', encoding='utf-8') as f:
                f.write(log_entry)

    if conflict_details and not args.force_vault:
        sys.exit(4)


if __name__ == '__main__':
    main()
