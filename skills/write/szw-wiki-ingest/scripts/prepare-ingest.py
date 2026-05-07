#!/usr/bin/env python3
"""prepare-ingest.py — Phase 0：为 /szw-wiki-ingest 收集决策上下文。

输入：
  --target DIR            Column 根（默认 cwd）
  --resource <rel-path>   待 ingest 的 resources/<file>.md（相对 target）
  --force                 即使 processed=true 也继续

输出 JSON 到 stdout（供主对话决策树消费）：
{
  "resource": {
    "path": "resources/<file>.md",
    "frontmatter": {...},
    "body_excerpt": "...",
    "body_full_chars": int,
    "already_processed": false
  },
  "existing_wiki_pages": {
    "concepts": [{"slug": "...", "title": "...", "status": "stub"}, ...],
    "people": [...],
    ...
  },
  "related_pages_by_tag": {
    "<tag>": ["wiki/topics/x.md", ...]
  },
  "wiki_link_map": {
    "wiki/concepts/llm-wiki-pattern.md": {"title": "...", "status": "active"}
  },
  "config": {
    "ingest_pages_per_source_max": 15
  }
}

退出码：
  0  成功
  1  非 szw column / wiki 未启用
  2  resource 不存在
  3  resource frontmatter 残缺（缺关键字段）
  4  resource processed=true（除非 --force）
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from frontmatter import parse_frontmatter  # noqa: E402


WIKI_TYPES = ['concepts', 'people', 'topics', 'frameworks', 'tools',
              'connections', 'hubs']

REQUIRED_RESOURCE_FIELDS = ['type', 'title', 'captured', 'lang']


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


def excerpt_body(body: str, max_chars: int) -> str:
    out = []
    total = 0
    for line in body.split('\n'):
        out.append(line)
        total += len(line) + 1
        if total >= max_chars:
            break
    return '\n'.join(out)[:max_chars]


def scan_wiki(target: Path) -> dict:
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
            rel = f'wiki/{type_name}/{f.name}'
            content = f.read_text(encoding='utf-8')
            metadata, _ = parse_frontmatter(content)
            pages[rel] = {
                'type': type_name,
                'slug': f.stem,
                'metadata': metadata,
            }
    return pages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--target', type=Path, default=Path.cwd())
    parser.add_argument('--resource', type=str, required=True,
                        help='Relative path to resources/<file>.md')
    parser.add_argument('--force', action='store_true',
                        help='Allow re-ingesting a processed resource')
    parser.add_argument('--excerpt-chars', type=int, default=2000,
                        help='Body excerpt length (default 2000)')
    args = parser.parse_args()

    target = args.target.resolve()
    config = load_config(target)

    if not config.get('wiki', {}).get('enabled'):
        print('ERROR: wiki.enabled=false; run /szw-wiki-init first',
              file=sys.stderr)
        sys.exit(1)

    res_rel = args.resource.lstrip('./')
    res_path = (target / res_rel).resolve()
    if not res_path.is_file():
        print(f'ERROR: resource not found: {res_rel}', file=sys.stderr)
        sys.exit(2)

    # Sanity: resource must live under resources/
    try:
        res_path.relative_to(target / 'resources')
    except ValueError:
        print(f'ERROR: resource must be under resources/: {res_rel}',
              file=sys.stderr)
        sys.exit(2)

    content = res_path.read_text(encoding='utf-8')
    metadata, body = parse_frontmatter(content)

    missing = [f for f in REQUIRED_RESOURCE_FIELDS if not metadata.get(f)]
    if missing:
        print(f'ERROR: resource frontmatter missing fields: {missing}',
              file=sys.stderr)
        sys.exit(3)

    already_processed = bool(metadata.get('processed'))
    if already_processed and not args.force:
        print(f'ERROR: resource already processed={metadata.get("processed")}; '
              f'pass --force to re-ingest', file=sys.stderr)
        sys.exit(4)

    # Scan existing wiki pages
    pages = scan_wiki(target)

    existing_wiki_pages: dict = {t: [] for t in WIKI_TYPES}
    wiki_link_map: dict = {}
    for rel, info in pages.items():
        m = info['metadata']
        entry = {
            'slug': info['slug'],
            'title': m.get('title', info['slug']),
            'status': m.get('status', 'stub'),
        }
        existing_wiki_pages[info['type']].append(entry)
        wiki_link_map[rel] = {
            'title': entry['title'],
            'status': entry['status'],
        }

    # related_pages_by_tag: only for tags this resource has
    res_tags = metadata.get('tags', []) or []
    related_pages_by_tag: dict = defaultdict(list)
    if res_tags:
        tagset = set(res_tags)
        for rel, info in pages.items():
            page_tags = info['metadata'].get('tags', []) or []
            for t in page_tags:
                if t in tagset:
                    related_pages_by_tag[t].append(rel)
    related_pages_by_tag = {k: sorted(set(v))
                            for k, v in related_pages_by_tag.items()}

    output = {
        'resource': {
            'path': str(res_path.relative_to(target)),
            'frontmatter': metadata,
            'body_excerpt': excerpt_body(body, args.excerpt_chars),
            'body_full_chars': len(body),
            'already_processed': already_processed,
        },
        'existing_wiki_pages': existing_wiki_pages,
        'related_pages_by_tag': related_pages_by_tag,
        'wiki_link_map': wiki_link_map,
        'config': {
            'ingest_pages_per_source_max':
                config.get('wiki', {}).get('ingest_pages_per_source_max', 15),
        },
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
