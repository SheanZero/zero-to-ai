#!/usr/bin/env python3
"""suggest.py — 给一个 article（或自由 thesis 文本）推荐相关 wiki 页 + resources。

输入两态：
  <slug>                  从 articles/<slug>/ARTICLE.md 提取 Thesis 段作为关键词源
  --thesis "<text>"       直接用文本作为关键词源

数据源：
  .zero/wiki-cache/pages.json       (rebuild-indexes 产出)
  .zero/wiki-cache/reverse.json
  .zero/wiki-cache/resources.json

排序公式（参 fan-llm-wiki-extension.md §7.6）：
  raw   = tag_overlap × 10 + title_hit × 5 + summary_hit × 2
  score = raw × type_weight × status_weight + inlinks × 0.5

退出码：
  0  成功
  1  非 szw column / wiki 未启用 / wiki-cache 缺失
  2  slug 不存在 / ARTICLE.md 缺失
  3  --thesis 与 slug 同时给（互斥）
  4  无可用关键词（thesis 为空 / 解析失败）
"""

import argparse
import json
import re
import sys
from pathlib import Path


WIKI_TYPES = ['connections', 'topics', 'concepts', 'tools', 'people',
              'frameworks', 'hubs']

TYPE_WEIGHT = {
    'connections': 5.0,
    'topics': 4.0,
    'concepts': 3.0,
    'tools': 2.5,
    'people': 2.0,
    'frameworks': 1.5,
    'hubs': 1.0,
}

STATUS_WEIGHT = {
    'mature': 3.0,
    'active': 2.0,
    'stub': 1.0,
}

# Stopwords for tokenization (very small set; v2 can extend).
ENGLISH_STOPS = {
    'the', 'and', 'for', 'with', 'this', 'that', 'from', 'into', 'about',
    'have', 'has', 'are', 'was', 'were', 'will', 'would', 'should', 'could',
    'how', 'why', 'what', 'when', 'where', 'who', 'which', 'one', 'two',
    'use', 'using', 'used', 'can', 'not', 'but', 'than', 'then', 'them',
    'they', 'their', 'there', 'here', 'also', 'just', 'only', 'more',
    'most', 'some', 'any', 'all', 'such', 'much', 'very', 'too',
}


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


def load_cache(target: Path) -> tuple[list, dict, list]:
    cache_dir = target / '.zero' / 'wiki-cache'
    pages_p = cache_dir / 'pages.json'
    reverse_p = cache_dir / 'reverse.json'
    resources_p = cache_dir / 'resources.json'
    if not pages_p.exists() or not reverse_p.exists():
        print(
            f'ERROR: wiki-cache missing; run rebuild-indexes.py first',
            file=sys.stderr,
        )
        sys.exit(1)
    pages = json.loads(pages_p.read_text(encoding='utf-8'))
    reverse = json.loads(reverse_p.read_text(encoding='utf-8'))
    resources = (
        json.loads(resources_p.read_text(encoding='utf-8'))
        if resources_p.exists() else []
    )
    return pages, reverse, resources


# ---------- keyword extraction ----------

_EN_TOKEN_RE = re.compile(r'[A-Za-z][A-Za-z0-9_-]{2,}')
_CJK_RE = re.compile(r'[一-鿿]+')
_CJK_PUNCT = (
    '，。！？；：、""''《》【】（）〈〉…—'
)


def extract_keywords(text: str) -> tuple[set, set]:
    """Return (english_terms, cjk_bigrams).

    english_terms: lowercase tokens, stopwords removed
    cjk_bigrams: 2-character sliding window over CJK runs
    """
    if not text:
        return set(), set()

    # Normalize whitespace + Chinese punctuation
    norm = text
    for p in _CJK_PUNCT:
        norm = norm.replace(p, ' ')

    en: set = set()
    for m in _EN_TOKEN_RE.finditer(norm):
        tok = m.group(0).lower()
        if tok in ENGLISH_STOPS:
            continue
        en.add(tok)

    cjk: set = set()
    for m in _CJK_RE.finditer(norm):
        run = m.group(0)
        for i in range(len(run) - 1):
            cjk.add(run[i:i + 2])

    return en, cjk


def parse_article_thesis(article_path: Path) -> str:
    """Extract '## Thesis' section content from ARTICLE.md."""
    if not article_path.is_file():
        return ''
    content = article_path.read_text(encoding='utf-8')

    # Strip frontmatter
    if content.startswith('---\n'):
        end = content.find('\n---\n', 4)
        if end != -1:
            content = content[end + 5:]

    # Find ## Thesis section
    lines = content.split('\n')
    in_section = False
    out: list = []
    for line in lines:
        s = line.strip()
        if s.lower().startswith('## thesis'):
            in_section = True
            continue
        if in_section and s.startswith('## '):
            break
        if in_section:
            out.append(line)
    text = '\n'.join(out).strip()

    # Also append H1 working title (first line) and frontmatter title for keywords
    raw = article_path.read_text(encoding='utf-8')
    fm_match = re.match(r'---\n(.*?)\n---', raw, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).split('\n'):
            m = re.match(r'^title:\s*(.+)$', line)
            if m:
                text = m.group(1).strip().strip('"').strip("'") + '\n' + text
                break

    return text


# ---------- scoring ----------

def compute_inlinks(pages: list) -> dict:
    """Map wiki page path → count of pages that reference it via related[]."""
    counts: dict = {}
    for p in pages:
        for r in p.get('related') or []:
            counts[r] = counts.get(r, 0) + 1
    return counts


def score_page(page: dict, en_kws: set, cjk_kws: set,
               inlinks: dict) -> tuple[float, dict]:
    """Return (score, breakdown)."""
    page_tags_lower = {t.lower() for t in (page.get('tags') or [])
                       if isinstance(t, str)}
    title = (page.get('title') or '').lower()
    summary = (page.get('summary_head') or '').lower()

    tag_overlap = page_tags_lower & en_kws
    title_hits = sum(1 for kw in en_kws if kw in title)
    title_hits += sum(1 for kw in cjk_kws if kw in title)
    summary_hits = sum(1 for kw in en_kws if kw in summary)
    summary_hits += sum(1 for kw in cjk_kws if kw in summary)

    raw = (
        len(tag_overlap) * 10.0
        + title_hits * 5.0
        + summary_hits * 2.0
    )
    if raw == 0:
        return 0.0, {}

    page_dir = page.get('type', '')
    type_w = TYPE_WEIGHT.get(_dir_for_type(page_dir), 1.0)
    status_w = STATUS_WEIGHT.get(page.get('status', 'stub'), 1.0)
    inlink_count = inlinks.get(page.get('path', ''), 0)
    score = raw * type_w * status_w + inlink_count * 0.5

    return score, {
        'tag_overlap': sorted(tag_overlap),
        'title_hits': title_hits,
        'summary_hits': summary_hits,
        'type_weight': type_w,
        'status_weight': status_w,
        'inlinks': inlink_count,
        'raw': raw,
    }


def _dir_for_type(t: str) -> str:
    """Reverse map singular type → plural directory name (for weight lookup)."""
    mapping = {
        'concept': 'concepts', 'person': 'people', 'topic': 'topics',
        'framework': 'frameworks', 'tool': 'tools',
        'connection': 'connections', 'hub': 'hubs',
    }
    return mapping.get(t, t)


def collect_related_resources(top_pages: list, resources: list,
                              max_per_page: int = 3) -> list:
    """For top wiki pages, list their sources (resources cited)."""
    by_path = {r['path']: r for r in resources}
    seen: set = set()
    out: list = []
    for p in top_pages:
        for src in (p.get('sources') or [])[:max_per_page]:
            if src in seen:
                continue
            seen.add(src)
            r = by_path.get(src)
            if r:
                out.append({
                    'path': src,
                    'title': r.get('title', src),
                    'tags': r.get('tags', []),
                })
    return out


# ---------- output ----------

def render_markdown(slug: str, source_label: str, by_type: dict,
                    related_resources: list, kw_summary: str) -> str:
    has_results = any(by_type.values())
    header = '## SUGGESTIONS READY' + ('' if has_results else ' (empty)')
    lines = [header, '']
    lines.append(f'For: {slug}')
    lines.append(f'Source: {source_label}')
    if kw_summary:
        lines.append(f'Keywords: {kw_summary}')
    if not has_results:
        lines.append('Reason: 0 wiki pages match keywords')
        lines.append('Suggestion: 扩 thesis 关键词，或用 '
                     '/szw-wiki-create-page 建相关 stub 后再 ingest')
    lines.append('')

    for t in WIKI_TYPES:
        items = by_type.get(t, [])
        if not items:
            continue
        lines.append(f'### {t} ({len(items)})')
        lines.append('')
        for entry in items:
            page = entry['page']
            why = entry['breakdown']
            tag_str = ''
            if why.get('tag_overlap'):
                tag_str = f' tags={",".join(why["tag_overlap"])}'
            lines.append(
                f'- **[{page["slug"]}]({page["path"]})** '
                f'`{page.get("status", "stub")}` '
                f'(score={entry["score"]:.1f}{tag_str})'
            )
            sm = page.get('summary_head', '').strip()
            if sm:
                lines.append(f'  {" ".join(sm.split())[:160]}')
        lines.append('')

    if related_resources:
        lines.append(f'### related resources ({len(related_resources)})')
        lines.append('')
        for r in related_resources[:10]:
            tag_str = (
                f' `[{",".join(r.get("tags", []))}]`' if r.get('tags') else ''
            )
            lines.append(f'- {r["path"]}{tag_str} — {r["title"]}')
        lines.append('')

    return '\n'.join(lines).rstrip() + '\n'


# ---------- main ----------

def cmd_main(args: argparse.Namespace) -> int:
    target = args.target.resolve()
    load_config(target)

    if args.thesis and args.slug:
        print('ERROR: --thesis and slug are mutually exclusive', file=sys.stderr)
        return 3

    if args.thesis:
        text = args.thesis
        slug_label = '<thesis>'
        source_label = '--thesis'
    elif args.slug:
        article_path = target / 'articles' / args.slug / 'ARTICLE.md'
        if not article_path.is_file():
            print(f'ERROR: article not found: {article_path}', file=sys.stderr)
            return 2
        text = parse_article_thesis(article_path)
        slug_label = args.slug
        source_label = f'articles/{args.slug}/ARTICLE.md'
    else:
        print('ERROR: provide <slug> or --thesis', file=sys.stderr)
        return 1

    en_kws, cjk_kws = extract_keywords(text)
    if not en_kws and not cjk_kws:
        print('ERROR: no usable keywords extracted from input', file=sys.stderr)
        return 4

    pages, reverse, resources = load_cache(target)
    inlinks = compute_inlinks(pages)

    # Filter by type
    if args.type:
        if args.type not in WIKI_TYPES:
            print(
                f'ERROR: invalid --type "{args.type}"; '
                f'expected one of {WIKI_TYPES}',
                file=sys.stderr,
            )
            return 1
        pages = [p for p in pages if _dir_for_type(p.get('type', '')) == args.type]

    # Score
    scored: list = []
    for p in pages:
        score, why = score_page(p, en_kws, cjk_kws, inlinks)
        if score > 0:
            scored.append({'page': p, 'score': score, 'breakdown': why})

    scored.sort(key=lambda x: (-x['score'], x['page']['slug']))
    top = scored[:args.limit]

    # Group by type
    by_type: dict = {t: [] for t in WIKI_TYPES}
    for entry in top:
        page_dir = _dir_for_type(entry['page'].get('type', ''))
        if page_dir in by_type:
            by_type[page_dir].append(entry)

    # Related resources from top pages
    related = collect_related_resources([e['page'] for e in top], resources)

    # Keyword summary
    kw_parts = []
    if en_kws:
        kw_parts.append(f'en={len(en_kws)}')
    if cjk_kws:
        kw_parts.append(f'cjk={len(cjk_kws)}')
    kw_summary = ' '.join(kw_parts)

    if args.json:
        out = {
            'slug': slug_label,
            'source': source_label,
            'keywords': {
                'english': sorted(en_kws),
                'cjk_bigrams': sorted(cjk_kws),
            },
            'suggestions_by_type': {
                t: [
                    {
                        'path': e['page']['path'],
                        'slug': e['page']['slug'],
                        'title': e['page'].get('title', ''),
                        'status': e['page'].get('status', 'stub'),
                        'score': round(e['score'], 2),
                        'breakdown': e['breakdown'],
                    }
                    for e in by_type[t]
                ]
                for t in WIKI_TYPES if by_type[t]
            },
            'related_resources': related,
            'total_matched': len(scored),
            'returned': len(top),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(slug_label, source_label, by_type, related,
                              kw_summary))

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('slug', nargs='?',
                        help='Article slug (reads articles/<slug>/ARTICLE.md)')
    parser.add_argument('--thesis', type=str,
                        help='Free-text input (mutually exclusive with slug)')
    parser.add_argument('--target', type=Path, default=Path.cwd())
    parser.add_argument('--limit', type=int, default=12,
                        help='Max suggestions returned (default 12)')
    parser.add_argument('--type', type=str,
                        help=f'Filter to one type: {WIKI_TYPES}')
    parser.add_argument('--json', action='store_true',
                        help='Output structured JSON instead of markdown')
    args = parser.parse_args()
    return cmd_main(args)


if __name__ == '__main__':
    sys.exit(main())
