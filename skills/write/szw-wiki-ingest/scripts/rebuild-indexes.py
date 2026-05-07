#!/usr/bin/env python3
"""
rebuild-indexes.py — 全量扫 wiki/ + resources/，重写 INDEX 文件 + 反向索引。

被 wiki-import.py 在 import 后自动调用；也可单独跑（如手动 ingest 后）。

输出:
  wiki/INDEX.md                    顶层入口（每类页数）
  wiki/<type>/INDEX.md  (×7)       该类下每页摘要
  resources/INDEX.md               按月分组
  .zero/wiki-cache/pages.json      wiki 页结构化
  .zero/wiki-cache/resources.json  resource 结构化
  .zero/wiki-cache/reverse.json    by_tag / by_type / by_status / by_resource / by_wiki_page
  .zero/wiki-cache/content-hash.json  每页 SHA256

Usage:
  rebuild-indexes.py [--target DIR] [--dry-run]

Exit codes:
  0  成功
  1  目标不是 szw Column / wiki 未启用
"""

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from frontmatter import parse_frontmatter  # noqa: E402


WIKI_TYPES = ['concepts', 'people', 'topics', 'frameworks', 'tools',
              'connections', 'hubs']

WIKI_TYPE_LABELS = {
    'concepts': '核心概念、术语',
    'people': '人物',
    'topics': '主题综述（多源融合）',
    'frameworks': '思维模型 / 方法论',
    'tools': '工具与项目（开源仓库、产品、技能集）',
    'connections': '跨主题关联（"洞察笔记"）',
    'hubs': 'MOC 导航页（页数 > 20 时启用）',
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def scan_wiki(target: Path):
    """Scan wiki/<type>/*.md. Returns dict: rel_path -> {metadata, body, hash}."""
    pages = {}
    wiki_root = target / 'wiki'
    if not wiki_root.is_dir():
        return pages
    for type_name in WIKI_TYPES:
        type_dir = wiki_root / type_name
        if not type_dir.is_dir():
            continue
        for f in sorted(type_dir.glob('*.md')):
            if f.name == 'INDEX.md':
                continue
            rel = str(f.relative_to(target))
            content = f.read_text(encoding='utf-8')
            metadata, body = parse_frontmatter(content)
            pages[rel] = {
                'path': rel,
                'type': type_name,
                'slug': f.stem,
                'metadata': metadata,
                'body_excerpt': _excerpt(body, 200),
                'hash': sha256_text(content),
            }
    return pages


def scan_resources(target: Path):
    """Scan resources/*.md. Returns dict: rel_path -> {metadata, body, hash}."""
    resources = {}
    res_root = target / 'resources'
    if not res_root.is_dir():
        return resources
    for f in sorted(res_root.glob('*.md')):
        if f.name == 'INDEX.md':
            continue
        rel = str(f.relative_to(target))
        content = f.read_text(encoding='utf-8')
        metadata, body = parse_frontmatter(content)
        resources[rel] = {
            'path': rel,
            'slug': f.stem,
            'metadata': metadata,
            'body_excerpt': _excerpt(body, 200),
            'hash': sha256_text(content),
        }
    return resources


def _excerpt(body: str, max_chars: int) -> str:
    """Get a short excerpt from body (skip headings)."""
    lines = []
    for line in body.split('\n'):
        s = line.strip()
        if not s:
            continue
        if s.startswith('#'):
            continue
        if s.startswith('>'):
            continue
        if s.startswith('```'):
            continue
        lines.append(s)
        if sum(len(l) for l in lines) >= max_chars:
            break
    text = ' '.join(lines)[:max_chars]
    return text.strip()


# ---------- INDEX rendering ----------

def render_card(slug: str, link_target: str, meta: dict, excerpt: str) -> str:
    """Render one INDEX entry card."""
    status = meta.get('status', 'stub')
    tags = meta.get('tags', [])
    tag_str = ''
    if tags:
        tag_list = ', '.join(tags) if isinstance(tags, list) else str(tags)
        tag_str = f' `[{tag_list}]`'
    summary = excerpt or meta.get('summary', '') or ''
    if summary:
        summary = ' '.join(summary.split())[:200]
    title = meta.get('title', slug)
    line = f'- **[{slug}]({link_target})** `{status}`{tag_str}'
    if title and title != slug:
        line += f' — {title}'
    if summary:
        line += f'\n  {summary}'
    return line


def render_wiki_index(target: Path, pages: dict, dry_run: bool):
    """Render wiki/INDEX.md (top-level)."""
    today = datetime.now().strftime('%Y-%m-%d')

    # Group by type
    by_type = defaultdict(list)
    for rel, info in pages.items():
        by_type[info['type']].append(info)

    lines = [
        '# Wiki — 知识层索引',
        '',
        '> 本 Column 维护的知识层（仿 [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 模式）。',
        '> 每个**内容页**都源自 `resources/` 中的具体素材。**Hub 页**不含新内容，只做导航（MOC）。',
        '> ingest / import 后自动更新本索引。',
        '',
        f'> Last rebuilt: {today}',
        '',
        '---',
        '',
        '## 子目录（6 类内容 + 1 类导航）',
        '',
    ]

    for type_name in WIKI_TYPES:
        count = len(by_type.get(type_name, []))
        label = WIKI_TYPE_LABELS[type_name]
        lines.append(f'- [{type_name}/]({type_name}/INDEX.md) — {label} ({count})')

    lines.extend([
        '',
        '---',
        '',
        '## 成熟度图例',
        '',
        '- `stub` — 初创，少量来源，待补充',
        '- `active` — 多来源，持续更新',
        '- `mature` — 主题稳定，结构良好',
        '',
        '---',
        '',
        '## 健康状态',
        '',
        f'- 最近 rebuild：{today}',
        f'- Wiki 页总数：{len(pages)}',
        f'- 待处理素材数：(运行 /szw-wiki-lint 查看)',
        f'- 孤立页面数：(同上)',
        '',
        '---',
        '',
        '## Sync Log',
        '',
        '> grep-friendly：`grep "^## \\[" log.md | tail -5`',
        '',
        '详见 [log.md](log.md)。',
        '',
    ])

    out = target / 'wiki' / 'INDEX.md'
    if not dry_run:
        out.write_text('\n'.join(lines), encoding='utf-8')


def render_type_index(target: Path, type_name: str, pages_of_type: list,
                      dry_run: bool):
    """Render wiki/<type>/INDEX.md."""
    today = datetime.now().strftime('%Y-%m-%d')
    label = WIKI_TYPE_LABELS[type_name]

    title_map = {
        'concepts': 'Concepts',
        'people': 'People',
        'topics': 'Topics',
        'frameworks': 'Frameworks',
        'tools': 'Tools',
        'connections': 'Connections',
        'hubs': 'Hubs',
    }

    lines = [
        f'# {title_map[type_name]}',
        '',
        f'> {label}。',
        '',
        f'> Last updated: {today}',
        f'> Page count: {len(pages_of_type)}',
        '',
        '---',
        '',
        '## Pages',
        '',
    ]

    if not pages_of_type:
        lines.append(
            f'(空 — 通过 `/szw-wiki-ingest` 或 '
            f'`/szw-wiki-create-page {type_name.rstrip("s")} <slug>` 添加)'
        )
    else:
        for info in sorted(pages_of_type, key=lambda x: x['slug']):
            line = render_card(
                slug=info['slug'],
                link_target=info['slug'] + '.md',
                meta=info['metadata'],
                excerpt=info['body_excerpt'],
            )
            lines.append(line)
            lines.append('')

    out = target / 'wiki' / type_name / 'INDEX.md'
    out.parent.mkdir(parents=True, exist_ok=True)
    if not dry_run:
        out.write_text('\n'.join(lines), encoding='utf-8')


def render_resources_index(target: Path, resources: dict, dry_run: bool):
    """Render resources/INDEX.md, grouped by month."""
    today = datetime.now().strftime('%Y-%m-%d')

    # Group by YYYY-MM (from filename or captured)
    by_month = defaultdict(list)
    for rel, info in resources.items():
        slug = info['slug']
        # Try to extract YYYY-MM from filename (YYYY-MM-DD-...)
        month = slug[:7] if len(slug) >= 7 and slug[4] == '-' and slug[7] == '-' else 'unknown'
        by_month[month].append(info)

    lines = [
        '# Resources — 原始素材库',
        '',
        '> wiki ingest 的唯一来源。所有素材必须有完整 frontmatter。',
        '>',
        '> 添加新素材的标准路径：',
        '> 1. 落 `inbox/sources/<YYYY-MM-DD-slug>.md`（read: false）',
        '> 2. 用户 review 后改 `read: true`',
        '> 3. 跑 `/szw-wiki-ingest --from-inbox` 自动迁移到此 + ingest 到 wiki',
        '',
        f'> Last rebuilt: {today}',
        f'> Resource count: {len(resources)}',
        '',
        '---',
        '',
    ]

    if not resources:
        lines.append('## 索引（按月分组）')
        lines.append('')
        lines.append('(空 — ingest 后自动填充)')
        lines.append('')
    else:
        lines.append('## 索引（按月分组，倒序）')
        lines.append('')
        for month in sorted(by_month.keys(), reverse=True):
            month_resources = by_month[month]
            lines.append(f'### {month} ({len(month_resources)})')
            lines.append('')
            for info in sorted(month_resources, key=lambda x: x['slug'], reverse=True):
                line = render_card(
                    slug=info['slug'],
                    link_target=info['slug'] + '.md',
                    meta=info['metadata'],
                    excerpt=info['body_excerpt'],
                )
                lines.append(line)
                lines.append('')

    lines.extend([
        '---',
        '',
        '## Frontmatter 必备字段',
        '',
        '详见 [`../wiki/CONVENTIONS.md`](../wiki/CONVENTIONS.md) §二。',
        '',
    ])

    out = target / 'resources' / 'INDEX.md'
    out.parent.mkdir(parents=True, exist_ok=True)
    if not dry_run:
        out.write_text('\n'.join(lines), encoding='utf-8')


# ---------- JSON caches ----------

def write_pages_json(cache_dir: Path, pages: dict, dry_run: bool):
    """Write pages.json (machine-readable wiki page index)."""
    entries = []
    for rel, info in sorted(pages.items()):
        m = info['metadata']
        entries.append({
            'path': rel,
            'type': info['type'],
            'slug': info['slug'],
            'title': m.get('title', info['slug']),
            'status': m.get('status', 'stub'),
            'tags': m.get('tags', []),
            'sources': m.get('sources', []),
            'related': m.get('related', []),
            'derived': m.get('derived', False),
            'created': m.get('created'),
            'updated': m.get('updated'),
            'summary_head': info['body_excerpt'],
            'sha256': info['hash'],
        })
    if not dry_run:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / 'pages.json').write_text(
            json.dumps(entries, indent=2, ensure_ascii=False) + '\n',
            encoding='utf-8'
        )


def write_resources_json(cache_dir: Path, resources: dict, dry_run: bool):
    """Write resources.json."""
    entries = []
    for rel, info in sorted(resources.items()):
        m = info['metadata']
        entries.append({
            'path': rel,
            'slug': info['slug'],
            'type': m.get('type', 'article'),
            'title': m.get('title', info['slug']),
            'lang': m.get('lang'),
            'tags': m.get('tags', []),
            'processed': m.get('processed', False),
            'wiki_pages': m.get('wiki_pages', []),
            'summary': m.get('summary', ''),
            'source_url': m.get('source'),
            'captured': m.get('captured'),
            'sha256': info['hash'],
        })
    if not dry_run:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / 'resources.json').write_text(
            json.dumps(entries, indent=2, ensure_ascii=False) + '\n',
            encoding='utf-8'
        )


def write_reverse_json(cache_dir: Path, pages: dict, resources: dict, dry_run: bool):
    """Write reverse.json (tag/type/status → pages; resource → pages)."""
    by_tag = defaultdict(list)
    by_type = defaultdict(list)
    by_status = defaultdict(list)
    by_wiki_page = defaultdict(list)  # wiki page → resources that cite it
    by_resource = defaultdict(list)   # resource → wiki pages that source it

    for rel, info in pages.items():
        m = info['metadata']
        by_type[info['type']].append(rel)
        by_status[m.get('status', 'stub')].append(rel)
        for t in m.get('tags', []):
            by_tag[t].append(rel)
        for src in m.get('sources', []):
            by_resource[src].append(rel)

    for rel, info in resources.items():
        m = info['metadata']
        for wp in m.get('wiki_pages', []):
            by_wiki_page[wp].append(rel)
        for t in m.get('tags', []):
            by_tag[t].append(rel)

    out = {
        'by_tag': {k: sorted(set(v)) for k, v in sorted(by_tag.items())},
        'by_type': {k: sorted(v) for k, v in sorted(by_type.items())},
        'by_status': {k: sorted(v) for k, v in sorted(by_status.items())},
        'by_resource': {k: sorted(v) for k, v in sorted(by_resource.items())},
        'by_wiki_page': {k: sorted(v) for k, v in sorted(by_wiki_page.items())},
    }

    if not dry_run:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / 'reverse.json').write_text(
            json.dumps(out, indent=2, ensure_ascii=False) + '\n',
            encoding='utf-8'
        )


def write_content_hash(cache_dir: Path, pages: dict, resources: dict, dry_run: bool):
    """Write content-hash.json (path → sha256)."""
    hashes = {}
    for rel, info in pages.items():
        hashes[rel] = info['hash']
    for rel, info in resources.items():
        hashes[rel] = info['hash']
    if not dry_run:
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / 'content-hash.json').write_text(
            json.dumps(hashes, indent=2, ensure_ascii=False, sort_keys=True) + '\n',
            encoding='utf-8'
        )


# ---------- Main ----------

def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--target', type=Path, default=Path.cwd())
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    target = args.target.resolve()

    config_path = target / '.zero' / 'szw-config.json'
    if not config_path.exists():
        print(f'ERROR: not an szw Column ({config_path} missing)', file=sys.stderr)
        sys.exit(1)

    try:
        config = json.loads(config_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        print(f'ERROR: szw-config.json parse failed: {e}', file=sys.stderr)
        sys.exit(1)

    if not config.get('wiki', {}).get('enabled'):
        print('ERROR: wiki.enabled=false; nothing to index', file=sys.stderr)
        sys.exit(1)

    pages = scan_wiki(target)
    resources = scan_resources(target)

    # Render INDEX files
    by_type = defaultdict(list)
    for rel, info in pages.items():
        by_type[info['type']].append(info)

    render_wiki_index(target, pages, args.dry_run)
    for type_name in WIKI_TYPES:
        render_type_index(target, type_name, by_type.get(type_name, []), args.dry_run)
    render_resources_index(target, resources, args.dry_run)

    # Write JSON caches
    cache_dir = target / '.zero' / 'wiki-cache'
    write_pages_json(cache_dir, pages, args.dry_run)
    write_resources_json(cache_dir, resources, args.dry_run)
    write_reverse_json(cache_dir, pages, resources, args.dry_run)
    write_content_hash(cache_dir, pages, resources, args.dry_run)

    # Report
    print(f"{'(dry-run) ' if args.dry_run else ''}Indexes rebuilt at: {target}\n")
    print(f"Wiki pages by type:")
    for type_name in WIKI_TYPES:
        count = len(by_type.get(type_name, []))
        print(f"  {type_name:13s} {count}")
    print(f"  total         {len(pages)}")
    print(f"\nResources: {len(resources)}")
    print(f"\nWritten files:")
    print(f"  wiki/INDEX.md")
    for type_name in WIKI_TYPES:
        print(f"  wiki/{type_name}/INDEX.md")
    print(f"  resources/INDEX.md")
    print(f"  .zero/wiki-cache/pages.json")
    print(f"  .zero/wiki-cache/resources.json")
    print(f"  .zero/wiki-cache/reverse.json")
    print(f"  .zero/wiki-cache/content-hash.json")


if __name__ == '__main__':
    main()
