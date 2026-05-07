#!/usr/bin/env python3
"""
prepare-research.py — Phase 0：收集 szw-research 所需上下文

用法:
  ./prepare-research.py [--slug <slug>]

行为:
  - 无 --slug：取 STATE.md Active Articles 表里 last_touched 最大且 status==brief_done 的 slug
  - 解析 articles/<slug>/01-brief.md：提取 thesis / supporting_claims / evidence_needed 等
  - 给每条 supporting_claim 分配稳定 ID（C1, C2, ...）
  - 列已有 .zero/evidence/<topic>.md 供 AI 检查复用
  - 列 EDITORIAL_CONTEXT.md 路径（§10 Evidence Standards 若存在则提示 AI 读）
  - 输出 JSON 给 AI 用作 Phase 1/2（Codex 路由）的工作清单

退出码:
  0  成功
  1  不在专栏目录
  2  slug / ARTICLE.md / 01-brief.md 不存在
  3  STATE.md 缺失 / 默认路由失败（无 brief_done 文章）
  4  ARTICLE.md frontmatter 解析失败
  5  01-brief.md 关键节缺失（thesis / supporting_claims）

设计原则:
  - 只读，不修改任何文件
  - claim ID 由本脚本统一分配（C1..Cn 按 supporting_claims 顺序），下游脚本按此引用
  - 已有 evidence bank 只列摘要（topic + 路径 + mtime），让 AI 视相关性按需 Read
  - 与 prepare-discuss.py 的 STATE.md 解析共享同一套规则（占位行 / H2 段落定位）
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
EVIDENCE_DIR = ".zero/evidence"
EDITORIAL_CONTEXT_NAME = "EDITORIAL_CONTEXT.md"

PLACEHOLDER_RE = re.compile(r"^<.*>$")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|$")
HEADING_RE = re.compile(r"^##\s+(.+)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
BULLET_RE = re.compile(r"^-\s+(.+)$")

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


# ---------- STATE.md 解析（与 prepare-discuss.py 一致） ----------


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
    """优先 brief_done 状态、last_touched 最大；其次任意 active 状态最大"""
    brief_done = [r for r in rows if r.get("Status", "").strip() == "brief_done"]
    if brief_done:
        valid = [r for r in brief_done if DATE_RE.match(r.get("Last touched", ""))]
        if valid:
            valid.sort(key=lambda r: r["Last touched"], reverse=True)
            return valid[0].get("Slug", "").strip() or None
    # 兜底：任何 active 状态
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


# ---------- 01-brief.md 解析 ----------


def extract_section_lines(body: str, heading: str) -> list[str]:
    """提取指定 H2 段落的正文行（不含标题；保留空行；去前后空白行）"""
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

    thesis_lines = extract_section_lines(content, "Thesis")
    payoff_lines = extract_section_lines(content, "Reader Payoff")
    claims_lines = extract_section_lines(content, "Supporting Claims")
    counter_lines = extract_section_lines(content, "Counterargument")
    evidence_needed_lines = extract_section_lines(content, "Evidence Needed")
    out_of_scope_lines = extract_section_lines(content, "Out of Scope")
    target_platforms_lines = extract_section_lines(content, "Target Platforms")

    supporting_claims = parse_bullet_list(claims_lines)
    evidence_needed = parse_bullet_list(evidence_needed_lines)
    out_of_scope = parse_bullet_list(out_of_scope_lines)

    return {
        "thesis": join_paragraph(thesis_lines),
        "reader_payoff": join_paragraph(payoff_lines),
        "supporting_claims": supporting_claims,
        "counterargument": join_paragraph(counter_lines),
        "evidence_needed": evidence_needed,
        "out_of_scope": out_of_scope,
        "target_platforms_text": join_paragraph(target_platforms_lines),
    }


def assign_claim_ids(claims: list[str]) -> list[dict[str, str]]:
    """C1, C2, ... 顺序绑定。后续 finalize 必须按此 ID 提交 evidence/diagnosis"""
    return [{"id": f"C{i + 1}", "text": text} for i, text in enumerate(claims)]


# ---------- evidence bank 列表 ----------


def list_evidence_bank(column_root: Path) -> list[dict[str, str]]:
    evidence_dir = column_root / EVIDENCE_DIR
    if not evidence_dir.exists():
        return []
    items = []
    for f in sorted(evidence_dir.iterdir()):
        if not f.is_file() or f.suffix != ".md":
            continue
        if f.parent.name == "retired":
            continue
        mtime = datetime.fromtimestamp(f.stat().st_mtime).date().isoformat()
        items.append(
            {
                "topic": f.stem,
                "path": str(f.relative_to(column_root)),
                "modified": mtime,
                "size_bytes": f.stat().st_size,
            }
        )
    return items


# ---------- main ----------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Prepare szw-research context")
    parser.add_argument("--slug", default=None)
    args = parser.parse_args(argv[1:])

    try:
        column_root = find_column_root(Path.cwd())
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    # 路由 slug
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
                "Use /szw-new-article + /szw-discuss first.",
                file=sys.stderr,
            )
            return 3

    # 验证文件
    article_dir = column_root / ARTICLES_DIR / slug
    article_md = article_dir / "ARTICLE.md"
    brief_md = article_dir / "01-brief.md"
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
    evidence_bank = list_evidence_bank(column_root)
    editorial_context = column_root / EDITORIAL_CONTEXT_NAME

    warnings = []
    current_status = fm.get("status")
    if current_status != "brief_done":
        if current_status == "research_done":
            warnings.append(
                "status='research_done'; re-running /szw-research will overwrite "
                "02-research.md and append duplicate evidence to evidence bank"
            )
        elif current_status in {"created"}:
            warnings.append(
                "status='created'; brief seems out of sync — consider re-running "
                "/szw-discuss to confirm brief is committed"
            )
        else:
            warnings.append(
                f"status='{current_status}' (not 'brief_done'); proceeding anyway"
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
        "existing_evidence_topics": evidence_bank,
        "editorial_context_path": (
            str(editorial_context.relative_to(column_root))
            if editorial_context.exists()
            else None
        ),
        "warnings": warnings,
    }

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
