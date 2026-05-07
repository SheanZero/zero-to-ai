#!/usr/bin/env python3
"""
prepare-discuss.py — Phase 0：收集 szw-discuss 所需上下文

用法:
  ./prepare-discuss.py [--slug <slug>]

行为:
  - 无 --slug：取 STATE.md Active Articles 表里 last_touched 最大的 slug
  - 验证 articles/<slug>/ARTICLE.md 存在；解析其 frontmatter
  - 列出 editorial-adr/*.md 的 ID + 标题
  - 返回 EDITORIAL_CONTEXT.md / COLUMN.md 的路径（让 AI 按需 Read）
  - 输出 JSON 给 AI 用作 grill 阶段的对齐基础

退出码:
  0  成功
  1  不在专栏目录（找不到 .zero/szw-config.json）
  2  slug 不存在（articles/<slug>/ARTICLE.md 缺失）
  3  STATE.md 缺失 / 解析失败 / Active Articles 为空（默认路由失败）
  4  ARTICLE.md frontmatter 解析失败

设计原则:
  - 只读，不修改任何文件
  - 给 AI 完整上下文一次性返回，避免 grill phase 反复 read 文件
  - ADR 内容不全文返回（只返回标题 + 路径），让 AI 真有需要才精确 Read
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

CONFIG_REL_PATH = ".zero/szw-config.json"
STATE_REL_PATH = ".zero/STATE.md"
ARTICLES_DIR = "articles"
ADR_DIR = "editorial-adr"
EDITORIAL_CONTEXT_NAME = "EDITORIAL_CONTEXT.md"
COLUMN_NAME = "COLUMN.md"

PLACEHOLDER_RE = re.compile(r"^<.*>$")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|$")
HEADING_RE = re.compile(r"^##\s+(.+)$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ADR_FILENAME_RE = re.compile(r"^(\d{4})-(.+)\.md$")
ADR_TITLE_RE = re.compile(r"^#\s+(.+)$")

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


# ---------- STATE.md 解析（仅取最新 active slug） ----------


def parse_active_table_rows(state_md_path: Path) -> list[dict[str, str]]:
    """
    返回 ## Active Articles 表的非占位数据行，dict[列名 → 值]。
    依赖与 szw-progress/scripts/parse-state.py 相同的占位规则。
    """
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


def pick_latest_active_slug(rows: list[dict[str, str]]) -> str | None:
    if not rows:
        return None
    # last_touched 列是 YYYY-MM-DD；按字典序就是时间序
    valid = [r for r in rows if DATE_RE.match(r.get("Last touched", ""))]
    if not valid:
        return None
    valid.sort(key=lambda r: r["Last touched"], reverse=True)
    return valid[0].get("Slug", "").strip() or None


# ---------- ARTICLE.md frontmatter 解析 ----------


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """
    简单 YAML-ish 解析。支持:
      - key: value
      - key: [a, b, c]      → list
      - key: null            → None
      - 字符串保持原样（不去引号）
    返回 (frontmatter_dict, body_after_frontmatter)
    """
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
            if not inner:
                fm[key] = []
            else:
                fm[key] = [item.strip() for item in inner.split(",") if item.strip()]
        else:
            fm[key] = val
    return fm, body


def extract_section(body: str, heading: str) -> str:
    """从 markdown body 提取指定 H2 段落的正文（不含标题；去首尾空白）。"""
    pattern = re.compile(
        r"^##\s+" + re.escape(heading) + r"\s*\n(.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(body)
    if not m:
        return ""
    return m.group(1).strip()


# ---------- ADR 列表 ----------


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
        adr_id = m.group(1)
        # 提取 H1 作为标题
        title = ""
        for line in f.read_text(encoding="utf-8").splitlines():
            tm = ADR_TITLE_RE.match(line)
            if tm:
                title = tm.group(1).strip()
                break
        adrs.append({
            "id": adr_id,
            "title": title or f.stem,
            "path": str(f.relative_to(column_root)),
        })
    return adrs


# ---------- main ----------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Prepare szw-discuss context")
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
        slug = pick_latest_active_slug(rows)
        if not slug:
            print(
                "ERROR: no active articles in STATE.md. "
                "Use /szw-new-article first.",
                file=sys.stderr,
            )
            return 3

    # 验证 article 存在
    article_dir = column_root / ARTICLES_DIR / slug
    article_md = article_dir / "ARTICLE.md"
    if not article_md.exists():
        print(
            f"ERROR: ARTICLE.md not found at {article_md.relative_to(column_root)}",
            file=sys.stderr,
        )
        return 2

    # 解析 frontmatter + body 段落
    raw = article_md.read_text(encoding="utf-8")
    try:
        fm, body = parse_frontmatter(raw)
    except ValueError as e:
        print(f"ERROR: frontmatter parse failed: {e}", file=sys.stderr)
        return 4

    source_material = extract_section(body, "Source Material")
    thesis_section = extract_section(body, "Thesis")

    # 收集 ADR 列表
    adrs = list_adrs(column_root)

    # context 文件路径（让 AI 按需 Read）
    editorial_context = column_root / EDITORIAL_CONTEXT_NAME
    column_md = column_root / COLUMN_NAME

    payload = {
        "column_root": str(column_root),
        "slug": slug,
        "article_md_path": str(article_md.relative_to(column_root)),
        "article": {
            "frontmatter": fm,
            "current_status": fm.get("status"),
            "type": fm.get("type"),
            "title": fm.get("title"),
            "target_platforms": fm.get("target_platforms"),
            "linked_inbox": fm.get("linked_inbox"),
            "linked_series": fm.get("linked_series"),
            "thesis_section_current": thesis_section,
            "source_material": source_material,
        },
        "context_paths": {
            "editorial_context": str(editorial_context.relative_to(column_root))
            if editorial_context.exists()
            else None,
            "column_md": str(column_md.relative_to(column_root))
            if column_md.exists()
            else None,
        },
        "adrs": adrs,
        "warnings": [],
    }

    # 重复 discuss 警告
    if fm.get("status") and fm["status"] != "created":
        payload["warnings"].append(
            f"status='{fm['status']}' (not 'created'); re-running /szw-discuss will overwrite 01-brief.md and reset thesis"
        )

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
