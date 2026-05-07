#!/usr/bin/env python3
"""
prepare-write.py — Phase 0：收集 szw-write 所需上下文

用法:
  ./prepare-write.py [--slug <slug>] [--section <S<n>>]

行为:
  - 无 --slug：取 STATE.md last_touched 最大且 status ∈ {outline_done, research_done, brief_done, draft_done, review_failed, review_passed} 的 slug
    优先级：outline_done > research_done > brief_done > draft_done > review_failed > review_passed
  - 解析 01-brief.md（必需） + 03-outline.md（可选；存在则优先 mode=outline_driven）
  - 列 .zero/style-profile.md / EDITORIAL_CONTEXT.md / ADR / glossary 路径供 AI 按需 Read
  - 列 .zero/writing-history/<slug>/INDEX.md 最近快照（如果存在）
  - 推荐 mode（first_draft / polish_after_review / continued_polish）
  - --section S<n> 时只输出该 section 的上下文 + 当前 04-draft.md 中该节的现有内容

退出码:
  0  成功
  1  不在专栏目录
  2  slug / ARTICLE.md / 01-brief.md 不存在
  3  STATE.md 缺失 / 默认路由失败
  4  ARTICLE.md frontmatter 解析失败
  5  --section 指定但 outline 缺失（v1.0 brief_only 路径不支持 section 模式）/ section 编号超出范围

设计原则:
  - 只读，不修改任何文件
  - section ID 稳定接口：outline 的 §1..§N 映射到 S1..SN；prepare 输出每节的 7 字段供 AI 起稿
  - 不解析 04-draft.md 的全部内容；仅在 --section 模式下提取该节
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

CONFIG_REL_PATH = ".zero/szw-config.json"
STATE_REL_PATH = ".zero/STATE.md"
ARTICLES_DIR = "articles"
ADR_DIR = "editorial-adr"
GLOSSARY_DIR = "glossary"
EDITORIAL_CONTEXT_NAME = "EDITORIAL_CONTEXT.md"
STYLE_PROFILE_REL = ".zero/style-profile.md"
WRITING_HISTORY_DIR = ".zero/writing-history"

PLACEHOLDER_RE = re.compile(r"^<.*>$")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|$")
HEADING_RE = re.compile(r"^##\s+(.+)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
BULLET_RE = re.compile(r"^-\s+(.+)$")
SECTION_ID_RE = re.compile(r"^S(\d+)$")
ADR_FILENAME_RE = re.compile(r"^(\d{4})-(.+)\.md$")
ADR_TITLE_RE = re.compile(r"^#\s+(.+)$")

STATUS_PRIORITY = [
    "outline_done",
    "research_done",
    "brief_done",
    "draft_done",
    "review_failed",
    "review_passed",
]


# ---------- column root ----------


def find_column_root(start: Path) -> Path:
    cur = start.resolve()
    while True:
        if (cur / CONFIG_REL_PATH).exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise FileNotFoundError(
        f"szw-config.json not found in {start} or any parent directory.\n"
        "Run /szw-init first to initialize a column."
    )


# ---------- STATE.md 解析 ----------


def parse_active_table_rows(state_md_path: Path) -> list[dict[str, str]]:
    if not state_md_path.exists():
        raise FileNotFoundError(f"STATE.md not found: {state_md_path}")
    lines = state_md_path.read_text(encoding="utf-8").splitlines()
    in_section = False
    headers: list[str] | None = None
    rows: list[dict[str, str]] = []
    for line in lines:
        m = HEADING_RE.match(line)
        if m:
            if m.group(1).strip() == "Active Articles":
                in_section = True
                headers = None
                continue
            elif in_section:
                break
            else:
                continue
        if not in_section:
            continue
        if TABLE_SEP_RE.match(line):
            continue
        m_row = TABLE_ROW_RE.match(line)
        if not m_row:
            continue
        cells = [c.strip() for c in m_row.group(1).split("|")]
        if headers is None:
            headers = cells
            continue
        if len(cells) != len(headers):
            continue
        if any(PLACEHOLDER_RE.match(c) for c in cells):
            continue
        if all(c == "" for c in cells):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def pick_default_slug(rows: list[dict[str, str]]) -> str | None:
    """按 STATUS_PRIORITY 顺序找；同 status 内按 last_touched 降序"""
    for status in STATUS_PRIORITY:
        bucket = [r for r in rows if r.get("Status", "").strip() == status]
        valid = [r for r in bucket if DATE_RE.match(r.get("Last touched", ""))]
        if valid:
            valid.sort(key=lambda r: r["Last touched"], reverse=True)
            return valid[0].get("Slug", "").strip() or None
    # 兜底：任意 active
    valid = [r for r in rows if DATE_RE.match(r.get("Last touched", ""))]
    if not valid:
        return None
    valid.sort(key=lambda r: r["Last touched"], reverse=True)
    return valid[0].get("Slug", "").strip() or None


# ---------- ARTICLE.md frontmatter ----------


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    if not content.startswith("---\n"):
        raise ValueError("frontmatter missing leading '---'")
    end_idx = content.find("\n---\n", 4)
    if end_idx < 0:
        raise ValueError("frontmatter missing closing '---'")
    fm_block = content[4:end_idx]
    body = content[end_idx + len("\n---\n") :]
    fm: dict[str, Any] = {}
    for line in fm_block.splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if val == "null" or val == "":
            fm[key] = None
        elif val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            fm[key] = (
                [item.strip() for item in inner.split(",") if item.strip()]
                if inner
                else []
            )
        else:
            fm[key] = val
    return fm, body


# ---------- 01-brief.md / 03-outline.md 解析 ----------


def extract_section_lines(body: str, heading: str) -> list[str]:
    pattern = re.compile(
        r"^##[ \t]+" + re.escape(heading) + r"[ \t]*\n(.*?)(?=^##[ \t]+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(body)
    if not m:
        return []
    text = m.group(1).strip()
    return text.splitlines() if text else []


def parse_bullet_list(lines: list[str]) -> list[str]:
    items = []
    for line in lines:
        m = BULLET_RE.match(line.strip())
        if m:
            items.append(m.group(1).strip())
    return items


def join_paragraph(lines: list[str]) -> str:
    return "\n".join(lines).strip()


def parse_brief(brief_md_path: Path) -> dict[str, Any]:
    content = brief_md_path.read_text(encoding="utf-8")
    return {
        "thesis": join_paragraph(extract_section_lines(content, "Thesis")),
        "reader_payoff": join_paragraph(extract_section_lines(content, "Reader Payoff")),
        "supporting_claims": parse_bullet_list(
            extract_section_lines(content, "Supporting Claims")
        ),
        "counterargument": join_paragraph(extract_section_lines(content, "Counterargument")),
        "evidence_needed": parse_bullet_list(
            extract_section_lines(content, "Evidence Needed")
        ),
        "out_of_scope": parse_bullet_list(
            extract_section_lines(content, "Out of Scope")
        ),
        "target_platforms_text": join_paragraph(
            extract_section_lines(content, "Target Platforms")
        ),
    }


def parse_outline_sections(outline_md_path: Path) -> list[dict[str, Any]]:
    """
    解析 03-outline.md 的 §2 Section Slices。
    每节格式（finalize-outline.py 渲染）：
      ### §1. <title>
      - **Core claim**: ...
      - **Evidence needed**: ...
      - **Reader payoff**: ...
      - **Programmer implication**: ...
      - **Counterargument**: ...
      - **Acceptance criteria**:
        - AC1: ...
        - AC2: ...
    """
    content = outline_md_path.read_text(encoding="utf-8")
    # 先定位 ## §2 Section Slices 段
    slices_block_re = re.compile(
        r"^##[ \t]+§2[\.\s][^\n]*\n(.*?)(?=^##[ \t]|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = slices_block_re.search(content)
    if not m:
        # fallback: 试 H2 含 "Section Slices"
        m = re.search(
            r"^##[ \t]+[^\n]*Section Slices[^\n]*\n(.*?)(?=^##[ \t]|\Z)",
            content,
            re.MULTILINE | re.DOTALL,
        )
    if not m:
        return []
    block = m.group(1)

    # 切 ### §<n>. <title>
    section_re = re.compile(
        r"^###[ \t]+§(\d+)[\.\s][ \t]*([^\n]*)\n(.*?)(?=^###[ \t]+§\d+[\.\s]|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    sections = []
    for sm in section_re.finditer(block):
        n = int(sm.group(1))
        title = sm.group(2).strip()
        body = sm.group(3).strip()

        # 提取字段（按 finalize-outline 的渲染格式）
        def extract_field(name: str) -> str:
            pattern = re.compile(
                r"^-[ \t]+\*\*"
                + re.escape(name)
                + r"\*\*[：:][ \t]*([^\n]*)",
                re.MULTILINE,
            )
            mm = pattern.search(body)
            return mm.group(1).strip() if mm else ""

        # acceptance_criteria 是嵌套 bullet
        ac_block_re = re.compile(
            r"^-[ \t]+\*\*Acceptance criteria\*\*[：:][ \t]*\n((?:[ \t]+-[ \t]+[^\n]+\n?)+)",
            re.MULTILINE,
        )
        ac_m = ac_block_re.search(body)
        ac_list = []
        if ac_m:
            for line in ac_m.group(1).splitlines():
                bm = re.match(r"^[ \t]+-[ \t]+(.+)$", line)
                if bm:
                    ac_list.append(bm.group(1).strip())

        sections.append(
            {
                "id": f"S{n}",
                "n": n,
                "title": title,
                "core_claim": extract_field("Core claim"),
                "evidence_needed": extract_field("Evidence needed"),
                "reader_payoff": extract_field("Reader payoff"),
                "programmer_implication": extract_field("Programmer implication"),
                "counterargument": extract_field("Counterargument"),
                "acceptance_criteria": ac_list,
            }
        )
    return sections


def derive_sections_from_brief(brief: dict[str, Any]) -> list[dict[str, Any]]:
    """v1.0 兜底：每条 supporting_claim 一节"""
    sections = []
    for i, claim in enumerate(brief["supporting_claims"], 1):
        sections.append(
            {
                "id": f"S{i}",
                "n": i,
                "title": claim[:60] + ("..." if len(claim) > 60 else ""),
                "core_claim": f"C{i}",
                "evidence_needed": (
                    "; ".join(brief["evidence_needed"])
                    if brief["evidence_needed"]
                    else ""
                ),
                "reader_payoff": brief["reader_payoff"],
                "programmer_implication": "",
                "counterargument": brief["counterargument"],
                "acceptance_criteria": [],
                "_derived_from_brief": True,
            }
        )
    return sections


# ---------- 04-draft.md 单节提取 ----------


def extract_draft_section(draft_md_path: Path, n: int) -> dict[str, str]:
    """从 04-draft.md 提取 ## §<n>. <title> 整节内容。"""
    content = draft_md_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"^(##[ \t]+§"
        + str(n)
        + r"[\.\s][^\n]*)\n(.*?)(?=^##[ \t]+§\d+[\.\s]|^##[ \t]+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(content)
    if not m:
        return {"found": False, "heading": "", "body": ""}
    return {
        "found": True,
        "heading": m.group(1),
        "body": m.group(2).rstrip(),
    }


# ---------- writing history ----------


def parse_history_index(slug_history_dir: Path) -> dict[str, Any]:
    index_path = slug_history_dir / "INDEX.md"
    snapshots = []
    if slug_history_dir.exists():
        for f in sorted(slug_history_dir.iterdir()):
            if f.is_file() and f.name != "INDEX.md" and f.suffix == ".md":
                snapshots.append(f.name)
    return {
        "exists": index_path.exists(),
        "snapshot_count": len(snapshots),
        "latest_snapshots": snapshots[-5:],  # 最近 5 个
    }


# ---------- ADR / glossary ----------


def list_adrs(column_root: Path) -> list[dict[str, str]]:
    adr_dir = column_root / ADR_DIR
    if not adr_dir.exists():
        return []
    adrs = []
    for f in sorted(adr_dir.iterdir()):
        if not f.is_file() or f.name == "INDEX.md":
            continue
        m = ADR_FILENAME_RE.match(f.name)
        if not m:
            continue
        title = ""
        for line in f.read_text(encoding="utf-8").splitlines():
            tm = ADR_TITLE_RE.match(line)
            if tm:
                title = tm.group(1).strip()
                break
        adrs.append(
            {
                "id": m.group(1),
                "title": title or f.stem,
                "path": str(f.relative_to(column_root)),
            }
        )
    return adrs


def list_glossary(column_root: Path) -> list[dict[str, str]]:
    gd = column_root / GLOSSARY_DIR
    if not gd.exists():
        return []
    items = []
    for f in sorted(gd.iterdir()):
        if not f.is_file() or f.suffix != ".md":
            continue
        items.append({"term": f.stem, "path": str(f.relative_to(column_root))})
    return items


# ---------- mode 推荐 ----------


def recommend_mode(current_status: str | None, draft_exists: bool) -> str:
    if not draft_exists:
        return "first_draft"
    if current_status == "review_failed":
        return "polish_after_review"
    if current_status in {"draft_done", "review_passed"}:
        return "continued_polish"
    return "first_draft"  # 兜底


# ---------- main ----------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Prepare szw-write context")
    parser.add_argument("--slug", default=None)
    parser.add_argument("--section", default=None, help="S<n> 形式（如 S2）")
    args = parser.parse_args(argv[1:])

    try:
        column_root = find_column_root(Path.cwd())
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    # slug 路由
    slug = args.slug
    if slug is None:
        try:
            rows = parse_active_table_rows(column_root / STATE_REL_PATH)
        except (FileNotFoundError, ValueError) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 3
        slug = pick_default_slug(rows)
        if not slug:
            print(
                "ERROR: no active articles in STATE.md. "
                "Run /szw-new-article and /szw-discuss first.",
                file=sys.stderr,
            )
            return 3

    article_dir = column_root / ARTICLES_DIR / slug
    article_md = article_dir / "ARTICLE.md"
    brief_md = article_dir / "01-brief.md"
    outline_md = article_dir / "03-outline.md"
    research_md = article_dir / "02-research.md"
    draft_md = article_dir / "04-draft.md"

    if not article_md.exists():
        print(
            f"ERROR: ARTICLE.md not found: {article_md.relative_to(column_root)}",
            file=sys.stderr,
        )
        return 2
    if not brief_md.exists():
        print(
            f"ERROR: 01-brief.md not found: {brief_md.relative_to(column_root)}\n"
            f"Run /szw-discuss {slug} first.",
            file=sys.stderr,
        )
        return 2

    raw = article_md.read_text(encoding="utf-8")
    try:
        fm, _ = parse_frontmatter(raw)
    except ValueError as e:
        print(f"ERROR: ARTICLE.md frontmatter parse failed: {e}", file=sys.stderr)
        return 4

    brief = parse_brief(brief_md)

    # sections
    if outline_md.exists():
        sections = parse_outline_sections(outline_md)
        sections_source = "outline"
    else:
        sections = derive_sections_from_brief(brief)
        sections_source = "brief_derived"

    # --section 校验
    section_ctx = None
    if args.section is not None:
        sm = SECTION_ID_RE.match(args.section)
        if not sm:
            print(
                f"ERROR: --section must be S<n> form (e.g. S1, S2); got {args.section!r}",
                file=sys.stderr,
            )
            return 5
        n = int(sm.group(1))
        target_section = next((s for s in sections if s["n"] == n), None)
        if not target_section:
            print(
                f"ERROR: section S{n} not found. Available: "
                f"{[s['id'] for s in sections]}",
                file=sys.stderr,
            )
            return 5
        if outline_md.exists():
            current_in_draft = (
                extract_draft_section(draft_md, n)
                if draft_md.exists()
                else {"found": False, "heading": "", "body": ""}
            )
            section_ctx = {
                "section": target_section,
                "current_in_draft": current_in_draft,
            }
        else:
            section_ctx = {
                "section": target_section,
                "current_in_draft": {"found": False, "heading": "", "body": ""},
                "warning": "outline 不存在；section 模式基于 brief 派生，replace 行为可能不精确",
            }

    # writing history
    slug_hist_dir = column_root / WRITING_HISTORY_DIR / slug
    history = parse_history_index(slug_hist_dir)

    # 长期资产
    style_profile_path = column_root / STYLE_PROFILE_REL
    editorial_context = column_root / EDITORIAL_CONTEXT_NAME
    adrs = list_adrs(column_root)
    glossary = list_glossary(column_root)

    current_status = fm.get("status")
    draft_exists = draft_md.exists()
    mode_reco = recommend_mode(current_status, draft_exists)

    warnings = []
    if not outline_md.exists():
        warnings.append(
            "03-outline.md missing → mode='brief_only'：起稿基于 brief 直接派生 sections; "
            "v2.0 严谨度建议先跑 /szw-outline"
        )
    if research_md.exists() and outline_md.exists():
        warnings.append(
            "02-research.md 存在；HIGH-risk claim 应在起稿用 safer_rewrite "
            "（见 02-research.md §3 Recommended Action）"
        )
    if not style_profile_path.exists():
        warnings.append(
            "style-profile.md 尚未生成（需要 szw-review Phase 2 跑过几次累积）；"
            "本次起稿无作者风格档案可参考"
        )

    payload = {
        "column_root": str(column_root),
        "slug": slug,
        "article_md_path": str(article_md.relative_to(column_root)),
        "brief_md_path": str(brief_md.relative_to(column_root)),
        "outline_md_path": (
            str(outline_md.relative_to(column_root)) if outline_md.exists() else None
        ),
        "research_md_path": (
            str(research_md.relative_to(column_root)) if research_md.exists() else None
        ),
        "draft_md_path": (
            str(draft_md.relative_to(column_root)) if draft_exists else None
        ),
        "current_status": current_status,
        "type": fm.get("type"),
        "title": fm.get("title"),
        "target_platforms": fm.get("target_platforms"),
        "brief": brief,
        "sections": sections,
        "sections_source": sections_source,
        "section_ctx": section_ctx,
        "mode_recommendation": mode_reco,
        "long_term_assets": {
            "style_profile": (
                str(style_profile_path.relative_to(column_root))
                if style_profile_path.exists()
                else None
            ),
            "editorial_context": (
                str(editorial_context.relative_to(column_root))
                if editorial_context.exists()
                else None
            ),
            "adrs": adrs,
            "glossary": glossary,
        },
        "writing_history": history,
        "warnings": warnings,
    }

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
