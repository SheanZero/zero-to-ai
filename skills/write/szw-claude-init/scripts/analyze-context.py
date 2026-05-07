#!/usr/bin/env python3
"""
analyze-context.py — 扫描目录上下文，输出 JSON 给主对话决定 CLAUDE.md / AGENTS.md 渲染策略。

Usage:
  analyze-context.py [--target DIR] [--include-existing-content]

Outputs structured JSON to stdout:

  {
    "target": str,
    "column_name": str,
    "project_type": "szw-column" | "vault" | "generic" | "docs-only" | "empty" | "unknown",
    "has_zero_config": bool,
    "config_summary": {...},
    "vault_path": str | null,
    "existing_files": {...},
    "existing_markers": {claude_md: [{section, version}, ...], agents_md: [...]},
    "directory_layout": [str],
    "warnings": [str]
  }

With --include-existing-content also includes:
  "preserved_user_content": {claude_md: str, agents_md: str}     # 标记块外内容
  "existing_section_content": {claude_md: {section: str}, ...}  # 标记块内现有内容

Exit codes:
  0  success
  1  target not a directory
"""

import argparse
import json
import re
import sys
from pathlib import Path


SECTION_MARKER_START_RE = re.compile(
    r'<!--\s*szw-init:auto-start\s*\[section:\s*([\w-]+)(?:,\s*version:\s*([\d.]+))?\s*\]\s*-->'
)
SECTION_MARKER_END_RE = re.compile(
    r'<!--\s*szw-init:auto-end\s*\[section:\s*([\w-]+)\s*\]\s*-->'
)


def parse_markers(filepath: Path):
    """解析文件中的 szw-init:auto 标记块。

    Returns (sections_list, preserved_user_content):
      sections_list: [{section, version, content, warning?}, ...]
      preserved_user_content: 所有标记块外的内容拼接
    """
    if not filepath.exists():
        return [], ""

    content = filepath.read_text(encoding='utf-8')
    sections = []
    preserved_parts = []

    cursor = 0
    while cursor < len(content):
        start_match = SECTION_MARKER_START_RE.search(content, cursor)
        if not start_match:
            preserved_parts.append(content[cursor:])
            break

        preserved_parts.append(content[cursor:start_match.start()])

        section_name = start_match.group(1)
        version = start_match.group(2) or "1.0"

        end_match = SECTION_MARKER_END_RE.search(content, start_match.end())
        if not end_match:
            sections.append({
                'section': section_name,
                'version': version,
                'content': content[start_match.end():].strip(),
                'warning': 'unclosed_marker',
            })
            break

        if end_match.group(1) != section_name:
            sections.append({
                'section': section_name,
                'version': version,
                'content': content[start_match.end():end_match.start()].strip(),
                'warning': f'mismatched_end:{end_match.group(1)}',
            })
        else:
            sections.append({
                'section': section_name,
                'version': version,
                'content': content[start_match.end():end_match.start()].strip(),
            })

        cursor = end_match.end()

    preserved_user_content = '\n'.join(
        p.strip() for p in preserved_parts if p.strip()
    )
    return sections, preserved_user_content


def detect_project_type(target: Path):
    """推断项目类型。Returns (type, warnings)."""
    warnings = []

    if (target / '.zero' / 'szw-config.json').exists():
        return 'szw-column', warnings

    vault_signals = ['0-Inbox', '1-wiki', '4-resources']
    if all((target / s).is_dir() for s in vault_signals):
        return 'vault', warnings
    partial_vault = [s for s in vault_signals if (target / s).is_dir()]
    if partial_vault:
        warnings.append(f'partial vault signals: {partial_vault}')

    generic_markers = ['package.json', 'pyproject.toml', 'Cargo.toml',
                       'go.mod', 'Gemfile', 'composer.json']
    if any((target / m).exists() for m in generic_markers):
        return 'generic', warnings

    if (target / '.git').is_dir():
        # has git but none of the package markers
        return 'generic', warnings

    md_files = list(target.glob('*.md'))
    visible = [f for f in target.iterdir()
               if not f.name.startswith('.') and f.name != '.DS_Store']

    if not visible:
        return 'empty', warnings

    if md_files and len(visible) <= len(md_files) + 2:
        return 'docs-only', warnings

    return 'unknown', warnings


def read_szw_config(target: Path):
    """Read .zero/szw-config.json + .local.json."""
    main_path = target / '.zero' / 'szw-config.json'
    local_path = target / '.zero' / 'szw-config.local.json'

    config = {}
    if main_path.exists():
        try:
            config['main'] = json.loads(main_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            config['main_error'] = str(e)

    if local_path.exists():
        try:
            config['local'] = json.loads(local_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            config['local_error'] = str(e)

    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--target', type=Path, default=Path.cwd(),
                        help='Target directory (default: cwd)')
    parser.add_argument('--include-existing-content', action='store_true',
                        help='Include preserved user content + existing section bodies')
    args = parser.parse_args()

    target = args.target.resolve()

    if not target.is_dir():
        print(json.dumps({'error': f'target not a directory: {target}'}),
              file=sys.stderr)
        sys.exit(1)

    project_type, warnings = detect_project_type(target)
    config = read_szw_config(target)
    main_config = config.get('main') or {}
    local_config = config.get('local') or {}

    wiki_cfg = main_config.get('wiki', {}) if isinstance(main_config, dict) else {}
    vault_local = local_config.get('vault', {}) if isinstance(local_config, dict) else {}

    claude_path = target / 'CLAUDE.md'
    agents_path = target / 'AGENTS.md'

    claude_sections, claude_preserved = parse_markers(claude_path)
    agents_sections, agents_preserved = parse_markers(agents_path)

    layout = []
    for f in sorted(target.iterdir()):
        if f.name == '.DS_Store':
            continue
        if f.name.startswith('.') and f.name not in {'.zero', '.gitignore', '.claude'}:
            continue
        layout.append(f.name + ('/' if f.is_dir() else ''))

    existing_files = {
        'claude_md': claude_path.exists(),
        'agents_md': agents_path.exists(),
        'column_md': (target / 'COLUMN.md').exists(),
        'editorial_context_md': (target / 'EDITORIAL_CONTEXT.md').exists(),
        'roadmap_md': (target / 'ROADMAP.md').exists(),
        'readme_md': (target / 'README.md').exists(),
        'gitignore': (target / '.gitignore').exists(),
        'wiki_dir': (target / 'wiki').is_dir(),
        'wiki_index': (target / 'wiki' / 'INDEX.md').exists(),
        'wiki_conventions': (target / 'wiki' / 'CONVENTIONS.md').exists(),
        'wiki_workflows': (target / 'wiki' / 'WORKFLOWS.md').exists(),
        'resources_dir': (target / 'resources').is_dir(),
        'assets_dir': (target / 'assets').is_dir(),
        'inbox_dir': (target / 'inbox').is_dir(),
        'inbox_sources_dir': (target / 'inbox' / 'sources').is_dir(),
        'articles_dir': (target / 'articles').is_dir(),
        'published_dir': (target / 'published').is_dir(),
        'editorial_adr_dir': (target / 'editorial-adr').is_dir(),
        'glossary_dir': (target / 'glossary').is_dir(),
        'zero_dir': (target / '.zero').is_dir(),
    }

    if config.get('main_error'):
        warnings.append(f'szw-config.json parse error: {config["main_error"]}')
    if config.get('local_error'):
        warnings.append(f'szw-config.local.json parse error: {config["local_error"]}')

    output = {
        'target': str(target),
        'column_name': target.name,
        'project_type': project_type,
        'has_zero_config': bool(main_config) and not config.get('main_error'),
        'config_summary': {
            'wiki_enabled': wiki_cfg.get('enabled'),
            'wiki_schema_version': wiki_cfg.get('schema_version'),
            'writing_lang': main_config.get('writing_lang') if isinstance(main_config, dict) else None,
            'vault_path_configured': bool(vault_local.get('path')),
        },
        'vault_path': vault_local.get('path'),
        'existing_files': existing_files,
        'existing_markers': {
            'claude_md': [
                {'section': s['section'], 'version': s['version'],
                 **({'warning': s['warning']} if 'warning' in s else {})}
                for s in claude_sections
            ],
            'agents_md': [
                {'section': s['section'], 'version': s['version'],
                 **({'warning': s['warning']} if 'warning' in s else {})}
                for s in agents_sections
            ],
        },
        'directory_layout': layout,
        'warnings': warnings,
    }

    if args.include_existing_content:
        output['preserved_user_content'] = {
            'claude_md': claude_preserved,
            'agents_md': agents_preserved,
        }
        output['existing_section_content'] = {
            'claude_md': {s['section']: s.get('content', '') for s in claude_sections},
            'agents_md': {s['section']: s.get('content', '') for s in agents_sections},
        }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
