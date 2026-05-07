#!/usr/bin/env python3
"""
finalize-wiki-init.py — 渲染 wiki schema 模板 + 启用 wiki.enabled + 同步 STATE.md。

Usage:
  finalize-wiki-init.py [--target DIR] [--bootstrap MODE] [--templates-dir DIR]
                        [--schema-only] [--dry-run]

  --target          目标 Column 根（默认 cwd）
  --bootstrap       seed-from-vault | empty-skeleton | schema-only（默认 empty-skeleton）
  --templates-dir   模板源（默认与脚本同目录的 ../templates）
  --schema-only     只渲染 CONVENTIONS.md / WORKFLOWS.md，跳过 INDEX 与 log
  --dry-run         只打印将要写的文件，不写盘

行为:
  1. 渲染 wiki schema 模板（含占位符替换）
  2. 写 wiki/CONVENTIONS.md, wiki/WORKFLOWS.md
  3. 渲染 wiki/INDEX.md, wiki/log.md, 7 类 INDEX.md, resources/INDEX.md
     （schema-only 模式跳过这些）
  4. 已存在的目标文件 → skip + 报告（不覆盖；用户应该手动 review）
  5. 更新 .zero/szw-config.json: wiki.enabled = true, schema_version 同步
  6. 更新 .zero/STATE.md: wiki_enabled / wiki_bootstrap 字段

退出码:
  0  成功
  1  target / templates dir 不存在
  2  非 szw Column
  3  wiki/ 目录未先创建（应先跑 init-wiki-layer.sh）
  4  szw-config.json 解析失败
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
import re


SCHEMA_VERSION = "1.2"


def render_placeholders(content: str, vars: dict) -> str:
    """简单占位符替换：<key> → vars[key]。"""
    for key, value in vars.items():
        content = content.replace(f'<{key}>', str(value) if value is not None else '')
    return content


def render_template(src: Path, dst: Path, vars: dict, dry_run: bool = False, skip_existing: bool = True):
    """复制模板，替换占位符，写到目标。"""
    if dst.exists() and skip_existing:
        return 'skipped'
    if not src.exists():
        return f'missing-template:{src}'
    content = render_placeholders(src.read_text(encoding='utf-8'), vars)
    if dry_run:
        return f'would-write:{len(content)}-chars'
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(content, encoding='utf-8')
    return 'written'


def update_szw_config(config_path: Path, schema_version: str, dry_run: bool = False):
    """启用 wiki + 同步 schema_version。"""
    if not config_path.exists():
        raise FileNotFoundError(f'{config_path} not found')
    config = json.loads(config_path.read_text(encoding='utf-8'))
    if 'wiki' not in config or not isinstance(config['wiki'], dict):
        config['wiki'] = {}
    config['wiki']['enabled'] = True
    config['wiki']['schema_version'] = schema_version
    config['wiki'].setdefault('ingest_batch_max', 5)
    config['wiki'].setdefault('ingest_pages_per_source_max', 15)
    config['wiki'].setdefault('lint_orphan_threshold_days', 180)
    config['wiki'].setdefault('auto_suggest_in_research', True)
    config['wiki'].setdefault('auto_suggest_in_discuss', True)
    config['wiki'].setdefault('evidence_confidence_default', 'medium')

    if dry_run:
        return f'would-set: wiki.enabled=true, schema_version={schema_version}'
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + '\n',
        encoding='utf-8'
    )
    return 'updated'


def update_state_md(state_path: Path, bootstrap_mode: str, dry_run: bool = False):
    """在 STATE.md 的 ## Column Status 段补充 wiki 字段（幂等）。"""
    if not state_path.exists():
        return 'missing'

    content = state_path.read_text(encoding='utf-8')
    today = datetime.now().strftime('%Y-%m-%d')

    # 处理 Wiki enabled 字段：插入或更新
    new_lines = []
    in_column_status = False
    seen_wiki_enabled = False
    seen_wiki_bootstrap = False
    inserted = False

    for line in content.split('\n'):
        if line.startswith('## Column Status'):
            in_column_status = True
            new_lines.append(line)
            continue
        if in_column_status and line.startswith('## '):
            # 离开 Column Status 段；如果之前没插入，现在插入
            if not seen_wiki_enabled and not inserted:
                new_lines.append(f'- Wiki enabled: true')
                new_lines.append(f'- Wiki bootstrap: {bootstrap_mode}')
                inserted = True
            in_column_status = False
            new_lines.append(line)
            continue
        if in_column_status:
            if 'Wiki enabled:' in line:
                new_lines.append(f'- Wiki enabled: true')
                seen_wiki_enabled = True
                continue
            if 'Wiki bootstrap:' in line:
                new_lines.append(f'- Wiki bootstrap: {bootstrap_mode}')
                seen_wiki_bootstrap = True
                continue
        new_lines.append(line)

    new_content = '\n'.join(new_lines)

    # 还在 Column Status 段结尾未插入（文件结尾就是该段）
    if in_column_status and not seen_wiki_enabled:
        new_content = new_content.rstrip() + f'\n- Wiki enabled: true\n- Wiki bootstrap: {bootstrap_mode}\n'

    # 更新顶部的 Updated 字段
    new_content = re.sub(
        r'^>\s*Updated:.*$',
        f'> Updated: {today}',
        new_content,
        count=1,
        flags=re.MULTILINE,
    )

    if dry_run:
        return 'would-update'
    state_path.write_text(new_content, encoding='utf-8')
    return 'updated'


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--target', type=Path, default=Path.cwd())
    parser.add_argument('--bootstrap', default='empty-skeleton',
                        choices=['seed-from-vault', 'empty-skeleton', 'schema-only'])
    parser.add_argument('--templates-dir', type=Path)
    parser.add_argument('--schema-only', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    target = args.target.resolve()

    if not target.is_dir():
        print(f'ERROR: target not a directory: {target}', file=sys.stderr)
        sys.exit(1)

    config_path = target / '.zero' / 'szw-config.json'
    if not config_path.exists():
        print(f'ERROR: not an szw Column ({config_path} missing)', file=sys.stderr)
        sys.exit(2)

    if not (target / 'wiki').is_dir():
        print(f'ERROR: wiki/ not found. Run init-wiki-layer.sh first.', file=sys.stderr)
        sys.exit(3)

    if args.templates_dir:
        templates_dir = args.templates_dir.resolve()
    else:
        templates_dir = (Path(__file__).parent.parent / 'templates').resolve()

    if not templates_dir.is_dir():
        print(f'ERROR: templates dir not found: {templates_dir}', file=sys.stderr)
        sys.exit(1)

    today = datetime.now().strftime('%Y-%m-%d')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    vars = {
        'YYYY-MM-DD': today,
        'INIT_TIMESTAMP': timestamp,
        'column_name': target.name,
        'schema_version': SCHEMA_VERSION,
    }

    # 渲染清单
    schema_files = [
        ('wiki/CONVENTIONS.md', 'wiki/CONVENTIONS.md'),
        ('wiki/WORKFLOWS.md', 'wiki/WORKFLOWS.md'),
    ]

    index_files = [
        ('wiki/INDEX.md', 'wiki/INDEX.md'),
        ('wiki/log.md', 'wiki/log.md'),
        ('wiki/concepts/INDEX.md', 'wiki/concepts/INDEX.md'),
        ('wiki/people/INDEX.md', 'wiki/people/INDEX.md'),
        ('wiki/topics/INDEX.md', 'wiki/topics/INDEX.md'),
        ('wiki/frameworks/INDEX.md', 'wiki/frameworks/INDEX.md'),
        ('wiki/tools/INDEX.md', 'wiki/tools/INDEX.md'),
        ('wiki/connections/INDEX.md', 'wiki/connections/INDEX.md'),
        ('wiki/hubs/INDEX.md', 'wiki/hubs/INDEX.md'),
        ('resources/INDEX.md', 'resources/INDEX.md'),
    ]

    files_to_render = list(schema_files)
    if not args.schema_only and args.bootstrap != 'schema-only':
        files_to_render.extend(index_files)

    results = []
    for tmpl_rel, dst_rel in files_to_render:
        src = templates_dir / tmpl_rel
        dst = target / dst_rel
        result = render_template(src, dst, vars, dry_run=args.dry_run, skip_existing=True)
        results.append((dst_rel, result))

    config_result = update_szw_config(config_path, SCHEMA_VERSION, dry_run=args.dry_run)
    state_result = update_state_md(target / '.zero' / 'STATE.md', args.bootstrap, dry_run=args.dry_run)

    print(f"\n{'(dry-run) ' if args.dry_run else ''}Wiki schema rendered at: {target}\n")
    print(f"Bootstrap mode: {args.bootstrap}")
    print(f"Schema version: {SCHEMA_VERSION}")
    print(f"\nFile results:")
    for path, status in results:
        status_icon = '✅' if status == 'written' else ('⏭️ ' if status == 'skipped' else '⚠️ ')
        print(f"  {status_icon} {path}: {status}")
    print(f"\nszw-config.json: {config_result}")
    print(f".zero/STATE.md: {state_result}")

    if args.bootstrap == 'seed-from-vault':
        print(f"\n👉 Next: /szw-wiki-import --full")
    else:
        print(f"\n👉 Next: 把素材放到 inbox/sources/，标 read=true 后跑 /szw-wiki-ingest --from-inbox")


if __name__ == '__main__':
    main()
