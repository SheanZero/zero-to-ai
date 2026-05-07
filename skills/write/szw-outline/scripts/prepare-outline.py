#!/usr/bin/env python3
"""
prepare-outline.py — Phase 0：收集 szw-outline 所需上下文

用法:
  ./prepare-outline.py [--slug <slug>]

行为:
  - 无 --slug：取 STATE.md last_touched 最大且 status ∈ {brief_done, research_done} 的 slug
  - 解析 articles/<slug>/01-brief.md（必需）：提取 thesis / supporting_claims / counterargument
  - 给每条 supporting_claim 分配稳定 ID（C1..Cn）—— 与 prepare-research.py 使用相同规则
  - 检查 02-research.md 是否存在；若存在仅返回路径（让 AI 按需 Read），不强行解析（research schema 由 szw-research 定，本脚本不依赖）
  - 输出 JSON 给 AI 用作 Phase 1（thesis-mapper）/ Phase 2（section-planner）的工作清单

退出码:
  0  成功
  1  不在专栏目录
  2  slug / ARTICLE.md / 01-brief.md 不存在
  3  STATE.md 缺失 / 默认路由失败
  4  ARTICLE.md frontmatter 解析失败
  5  01-brief.md 关键节缺失（thesis / supporting_claims）

设计原则:
  - 只读，不修改任何文件
  - claim ID 顺序与 prepare-research.py 保持一致（按 brief supporting_claims 顺序），下游产物按此引用
  - 02-research.md 为可选输入：存在则路径返回 + warning 提示 AI Read；不存在则 mode='brief_only' + 大 warning
  - 与 prepare-discuss / prepare-research 共享 STATE.md / brief 解析规则（占位行 / H2 段落定位 / bullet list）
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

PLACEHOLDER_RE = re.compile(r"^<.*>$")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|$")
HEADING_RE = re.compile(r"^##\s+(.+)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
BULLET_RE = re.compile(r"^-\s+(.+)$")

PREFERRED_STATUSES = {"brief_done", "research_done"}


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
    """
    优先级：
      1. status == research_done，按 last_touched 降序
      2. status == brief_done，按 last_touched 降序
      3. 兜底：任意有 last_touched 的 active 行，按降序
    """
    def by_date_desc(rs: list[dict[str, str]]) -> list[dict[str, str]]:
        valid = [r for r in rs if DATE_RE.match(r.get("Last touched", ""))]
        return sorted(valid, key=lambda r: r["Last touched"], reverse=True)

    for status in ("research_done", "brief_done"):
        bucket = [r for r in rows if r.get("Status", "").strip() == status]
        sorted_bucket = by_date_desc(bucket)
        if sorted_bucket:
            return sorted_bucket[0].get("Slug", "").strip() or None

    fallback = by_date_desc(rows)
    if not fallback:
        return None
    return fallback[0].get("Slug", "").strip() or None


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


# ---------- 01-brief.md 解析 ----------


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


def assign_claim_ids(claims: list[str]) -> list[dict[str, str]]:
    return [{"id": f"C{i + 1}", "text": text} for i, text in enumerate(claims)]


# ---------- main ----------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Prepare szw-outline context")
    parser.add_argument("--slug", default=None)
    args = parser.parse_args(argv[1:])

    try:
        column_root = find_column_root(Path.cwd())
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

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
                "Need at least one with status brief_done or research_done.",
                file=sys.stderr,
            )
            return 3

    article_dir = column_root / ARTICLES_DIR / slug
    article_md = article_dir / "ARTICLE.md"
    brief_md = article_dir / "01-brief.md"
    research_md = article_dir / "02-research.md"

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
    if not brief["thesis"] or not brief["supporting_claims"]:
        print(
            "ERROR: 01-brief.md missing critical sections (Thesis / Supporting Claims).\n"
            "Re-run /szw-discuss to regenerate brief.",
            file=sys.stderr,
        )
        return 5

    claims_with_ids = assign_claim_ids(brief["supporting_claims"])

    research_present = research_md.exists()
    research_meta = None
    if research_present:
        stat = research_md.stat()
        research_meta = {
            "path": str(research_md.relative_to(column_root)),
            "modified": datetime.fromtimestamp(stat.st_mtime).date().isoformat(),
            "size_bytes": stat.st_size,
        }

    warnings = []
    current_status = fm.get("status")
    if current_status == "outline_done":
        warnings.append(
            "status='outline_done'; re-running /szw-outline will overwrite 03-outline.md"
        )
    elif current_status not in PREFERRED_STATUSES:
        warnings.append(
            f"status='{current_status}' (not 'brief_done' or 'research_done'); proceeding anyway"
        )

    if not research_present:
        warnings.append(
            "02-research.md missing → mode='brief_only': AI works without evidence anchoring. "
            "Section slices will rely on brief.evidence_needed (planned, not verified). "
            "For v2.0 rigor run /szw-research first."
        )

    payload = {
        "column_root": str(column_root),
        "slug": slug,
        "article_md_path": str(article_md.relative_to(column_root)),
        "brief_md_path": str(brief_md.relative_to(column_root)),
        "current_status": current_status,
        "type": fm.get("type"),
        "title": fm.get("title"),
        "target_platforms": fm.get("target_platforms"),
        "brief": brief,
        "claims_with_ids": claims_with_ids,
        "research_md": research_meta,  # null if not present
        "mode": "brief_plus_research" if research_present else "brief_only",
        "warnings": warnings,
    }

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
