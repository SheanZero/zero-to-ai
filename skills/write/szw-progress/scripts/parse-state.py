#!/usr/bin/env python3
"""
parse-state.py — 解析 .zero/STATE.md，输出结构化 JSON 供 szw-progress 渲染

用法:
  ./parse-state.py active                      # 列所有 active articles + 推荐
  ./parse-state.py completed                   # 列 Recently Completed
  ./parse-state.py article <slug>              # 单 article 详细状态 + 阶段产物清单
  ./parse-state.py validate                    # 仅验证 STATE.md 可解析

退出码:
  0  成功
  1  STATE.md 不存在（提示先 /szw-init）
  2  目标不存在（如指定 slug 不在 active 表）
  3  STATE.md 解析失败（表结构损坏）

设计原则:
  - 输出 JSON，让 AI 决定如何渲染
  - 占位行（含 <...> 形式的字段）自动过滤
  - 自动从 cwd 向上找 .zero/STATE.md
  - 不修改 STATE.md（只读工具；写入由 szw-complete / szw-pause 等独立脚本负责）
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

STATE_REL_PATH = ".zero/STATE.md"
ARTICLES_REL_PATH = "articles"

# ---------- Status → 推荐下一命令 ----------

# 这份映射与 szw-help/SKILL.md "下一步推荐规则" 保持一致
# 改动须同步两处
STATUS_TO_NEXT: dict[str, dict[str, str]] = {
    "created": {
        "command": "/szw-discuss",
        "reason": "拷问选题，写 brief",
    },
    "brief_done": {
        "command": "/szw-research",
        "reason": "证据采集 + 判断诊断（v2.0）；v1.0 跳到 /szw-write",
    },
    "research_done": {
        "command": "/szw-outline",
        "reason": "论证地图 + 拆片",
    },
    "outline_done": {
        "command": "/szw-write",
        "reason": "起稿",
    },
    "draft_done": {
        "command": "/szw-review",
        "reason": "Codex 反审 + Phase 2 学风格",
    },
    "review_failed": {
        "command": "/szw-write",
        "args_hint": "[section] --mode polish",
        "reason": "修复 review HIGH issue（最优先级）",
    },
    "review_passed": {
        "command": "/szw-publish",
        "reason": "多平台打包",
    },
    "published": {
        "command": "/szw-complete",
        "reason": "终结流水线（移入 Recently Completed）",
    },
    "paused": {
        "command": "/szw-resume",
        "reason": "恢复上下文（已留 handoff，恢复成本低）",
    },
}

# 已知的阶段产物文件（按时间顺序；用于 article <slug> 详情列表）
# ARTICLE.md 始终是 required；其他阶段文件按 status 强约束
PHASE_FILES = [
    "01-brief.md",
    "02-research.md",
    "03-outline.md",
    "04-draft.md",
    "05-review.md",
]

# Status → 该 status 强约束的文件（除 ARTICLE.md 外）
# 不强约束 = 可能存在（v2.0 走过）也可能不存在（v1.0 跳过），用 status_required=False 渲染
STATUS_TO_REQUIRED_FILE: dict[str, str | None] = {
    "created": None,
    "brief_done": "01-brief.md",
    "research_done": "02-research.md",
    "outline_done": "03-outline.md",
    "draft_done": "04-draft.md",
    "review_failed": "05-review.md",
    "review_passed": "05-review.md",
    "published": "05-review.md",  # publish 自身产物在 published/ 目录，不在 article 目录
    "paused": None,
}

ACTIVE_STATUSES = set(STATUS_TO_NEXT.keys())  # 全是 active；终态 completed/archived 不在 STATE Active 表里

# ---------- 工具函数 ----------


def find_column_root(start: Path) -> Path:
    """从 cwd 向上找到含 .zero/STATE.md 的目录"""
    cur = start.resolve()
    while True:
        if (cur / STATE_REL_PATH).exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise FileNotFoundError(
        f"STATE.md not found in {start} or any parent directory.\n"
        "Run /szw-init first to initialize a column."
    )


def read_state_md(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------- Markdown 表解析 ----------

PLACEHOLDER_RE = re.compile(r"^<.*>$")  # 形如 <slug> / <YYYY-MM-DD> 视为占位
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HEADING_RE = re.compile(r"^##\s+(.+)$")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|$")


def parse_section_table(content: str, heading_text: str) -> list[dict[str, str]]:
    """
    在 STATE.md 中找到 ## <heading_text> 段落下的第一张表，返回 list of dict（列名 → 值）。

    规则:
      - 跳过表头分隔行（| --- | --- |）
      - 跳过占位行（任意单元格匹配 <...> 形式）
      - 遇到下一个 ## 标题或文档结尾停止
    """
    lines = content.splitlines()
    in_section = False
    headers: list[str] | None = None
    rows: list[dict[str, str]] = []

    for line in lines:
        line = line.rstrip()

        # 进入目标 section
        m = HEADING_RE.match(line)
        if m:
            section_title = m.group(1).strip()
            if section_title == heading_text:
                in_section = True
                headers = None
                continue
            elif in_section:
                # 离开目标 section
                break
            else:
                continue

        if not in_section:
            continue

        # 表行
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
            continue  # 残缺行跳过

        # 占位行过滤
        if any(PLACEHOLDER_RE.match(c) for c in cells):
            continue

        # 任何单元格全空也跳过
        if all(c == "" for c in cells):
            continue

        rows.append(dict(zip(headers, cells)))

    return rows


# ---------- 业务逻辑 ----------


def parse_date(s: str) -> date | None:
    """容错解析 YYYY-MM-DD；非法返回 None"""
    if not DATE_RE.match(s):
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def days_since(d: date | None) -> int | None:
    if d is None:
        return None
    return (date.today() - d).days


def priority_rank(status: str, last_touched: date | None) -> tuple[int, int]:
    """
    返回 (主优先级, 次优先级) —— 数值越小越优先。
    主优先级:
      0  review_failed
      1  paused
      2  其他
    次优先级 = -days_since（即越久未触碰排越前；同主级时）
    """
    if status == "review_failed":
        primary = 0
    elif status == "paused":
        primary = 1
    else:
        primary = 2

    days = days_since(last_touched)
    secondary = -days if days is not None else 0
    return (primary, secondary)


def enrich_article(row: dict[str, str], column_root: Path) -> dict[str, Any]:
    """
    给 STATE.md 的一行追加：
      - parsed last_touched (date) → days_since_touched
      - next_command / reason（按 status 查表；STATE.md 自带的 Next action 会优先保留为 state_md_hint）
      - priority_rank
      - article_dir / article_md_exists
    """
    slug = row.get("Slug", "").strip()
    status = row.get("Status", "").strip()
    last_touched_raw = row.get("Last touched", "").strip()
    state_md_hint = row.get("Next action", "").strip()

    parsed_date = parse_date(last_touched_raw)

    next_info = STATUS_TO_NEXT.get(status, {})

    article_dir = column_root / ARTICLES_REL_PATH / slug
    article_md = article_dir / "ARTICLE.md"

    rec_command = next_info.get("command", "")
    if rec_command and slug:
        rec_full = f"{rec_command} {slug}"
        if "args_hint" in next_info:
            rec_full = f"{rec_full} {next_info['args_hint']}"
    else:
        rec_full = state_md_hint or "(unknown)"

    return {
        "slug": slug,
        "status": status,
        "last_touched": last_touched_raw,
        "days_since_touched": days_since(parsed_date),
        "state_md_hint": state_md_hint,
        "next_command": next_info.get("command", ""),
        "next_command_full": rec_full,
        "next_reason": next_info.get("reason", ""),
        "priority_rank": list(priority_rank(status, parsed_date)),
        "article_dir": str(article_dir.relative_to(column_root)),
        "article_md_exists": article_md.exists(),
        "is_known_status": status in ACTIVE_STATUSES,
    }


def pick_global_recommendation(
    enriched: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """按 priority_rank 升序挑出最该做的"""
    if not enriched:
        return None
    sorted_arts = sorted(enriched, key=lambda a: tuple(a["priority_rank"]))
    top = sorted_arts[0]
    if top["status"] == "review_failed":
        bucket = "review_failed"
    elif top["status"] == "paused":
        bucket = "paused"
    elif top["days_since_touched"] is not None and top["days_since_touched"] >= 7:
        bucket = "stale"
    else:
        bucket = "most_recent"
    return {
        "slug": top["slug"],
        "command": top["next_command_full"],
        "status": top["status"],
        "reason": top["next_reason"],
        "priority_bucket": bucket,
    }


# ---------- 命令处理 ----------


def cmd_active(column_root: Path) -> int:
    content = read_state_md(column_root / STATE_REL_PATH)
    raw_rows = parse_section_table(content, "Active Articles")
    enriched = [enrich_article(r, column_root) for r in raw_rows]
    enriched.sort(key=lambda a: tuple(a["priority_rank"]))

    payload = {
        "column_root": str(column_root),
        "active_count": len(enriched),
        "articles": enriched,
        "global_recommendation": pick_global_recommendation(enriched),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_completed(column_root: Path) -> int:
    content = read_state_md(column_root / STATE_REL_PATH)
    raw_rows = parse_section_table(content, "Recently Completed")
    payload = {
        "column_root": str(column_root),
        "completed_count": len(raw_rows),
        "articles": raw_rows,  # 原样输出，列名: Slug / Completed at / Disposition / Platforms
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_article(column_root: Path, slug: str) -> int:
    content = read_state_md(column_root / STATE_REL_PATH)
    raw_rows = parse_section_table(content, "Active Articles")
    match = next((r for r in raw_rows if r.get("Slug", "").strip() == slug), None)

    if match is None:
        # 检查 Recently Completed
        completed_rows = parse_section_table(content, "Recently Completed")
        in_completed = any(
            r.get("Slug", "").strip() == slug for r in completed_rows
        )
        payload = {
            "column_root": str(column_root),
            "slug": slug,
            "found_in": "completed" if in_completed else None,
            "error": (
                "Article in Recently Completed (terminal state); use git log / archive."
                if in_completed
                else f"Slug '{slug}' not found in STATE.md Active Articles or Recently Completed."
            ),
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 2

    enriched = enrich_article(match, column_root)
    article_dir = column_root / enriched["article_dir"]
    required_phase_file = STATUS_TO_REQUIRED_FILE.get(enriched["status"])

    artifacts = []
    # ARTICLE.md 始终算 status_required
    artifacts.append(
        {
            "file": "ARTICLE.md",
            "exists": (article_dir / "ARTICLE.md").exists(),
            "status_required": True,
        }
    )
    # 各阶段文件：status_required = 是否被当前 status 强约束
    for fname in PHASE_FILES:
        fpath = article_dir / fname
        is_required = fname == required_phase_file
        # 跳过既不存在也不 required 的（避免列表噪声）
        if not fpath.exists() and not is_required:
            continue
        artifacts.append(
            {
                "file": fname,
                "exists": fpath.exists(),
                "status_required": is_required,
            }
        )

    enriched["artifacts"] = artifacts
    print(json.dumps(enriched, indent=2, ensure_ascii=False))
    return 0


def cmd_validate(column_root: Path) -> int:
    state_path = column_root / STATE_REL_PATH
    issues: list[str] = []
    try:
        content = read_state_md(state_path)
    except OSError as e:
        print(json.dumps({"valid": False, "issues": [f"read failed: {e}"]}, indent=2))
        return 3

    active_rows = parse_section_table(content, "Active Articles")
    completed_rows = parse_section_table(content, "Recently Completed")

    for r in active_rows:
        slug = r.get("Slug", "").strip()
        status = r.get("Status", "").strip()
        if not slug:
            issues.append(f"active row missing Slug: {r}")
        if status not in ACTIVE_STATUSES:
            issues.append(f"unknown status '{status}' for slug '{slug}'")
        if not parse_date(r.get("Last touched", "").strip()):
            issues.append(f"invalid Last touched date for slug '{slug}'")

    payload = {
        "valid": len(issues) == 0,
        "active_count": len(active_rows),
        "completed_count": len(completed_rows),
        "issues": issues,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["valid"] else 3


# ---------- main ----------


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1

    try:
        column_root = find_column_root(Path.cwd())
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    cmd = argv[1]
    args = argv[2:]

    if cmd == "active" and not args:
        return cmd_active(column_root)
    if cmd == "completed" and not args:
        return cmd_completed(column_root)
    if cmd == "article" and len(args) == 1:
        return cmd_article(column_root, args[0])
    if cmd == "validate" and not args:
        return cmd_validate(column_root)

    print(f"ERROR: unknown command or wrong arguments: {cmd} {args}", file=sys.stderr)
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
