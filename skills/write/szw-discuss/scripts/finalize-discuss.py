#!/usr/bin/env python3
"""
finalize-discuss.py — Phase 3：把 grill 结果落盘 + 推进状态

子命令:
  commit --slug <slug>          # 从 stdin 读 JSON brief 数据，渲染 01-brief.md，更新 ARTICLE.md / STATE.md
  abort  --slug <slug> --reason "..."   # grill 拷问失败：移到 articles/archived/<slug>/，从 STATE.md Active 表删除，加到 Recently Completed (archived)

commit stdin JSON schema（参考 references/brief-schema.md）:
  {
    "thesis": "...",
    "reader_payoff": "...",
    "supporting_claims": ["claim1", "claim2", ...],
    "counterargument": "...",
    "evidence_needed": ["..."],
    "out_of_scope": ["..."],
    "target_platforms": ["blog", "wechat"],   // 可覆盖 ARTICLE.md 原值
    "grill_qa": [
      {"q": "...", "user_answer": "...", "ai_recommendation": "...", "final": "..."}
    ],
    "alignment_check": {
      "adrs_consulted": ["0001"],
      "principles_consulted": ["P1"],
      "conflicts": [],          // 空数组 = 对齐通过
      "notes": "..."
    }
  }

退出码:
  0  成功
  1  不在专栏目录
  2  slug 不存在 / ARTICLE.md 缺失
  3  STATE.md 缺失或解析失败
  4  stdin JSON 解析失败 / 字段缺失
  5  alignment_check.conflicts 非空（拒绝 commit；让 AI 改用 abort 或修 brief）
  6  abort 时目标 archived 路径冲突
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any

CONFIG_REL_PATH = ".zero/szw-config.json"
STATE_REL_PATH = ".zero/STATE.md"
ARTICLES_DIR = "articles"
ARCHIVED_SUBDIR = "archived"

PLACEHOLDER_RE = re.compile(r"^<.*>$")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|$")
HEADING_RE = re.compile(r"^##\s+(.+)$")

REQUIRED_BRIEF_FIELDS = {
    "thesis",
    "reader_payoff",
    "supporting_claims",
    "counterargument",
    "evidence_needed",
    "out_of_scope",
    "grill_qa",
    "alignment_check",
}


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
        f"szw-config.json not found in {start} or any parent directory."
    )


# ---------- ARTICLE.md frontmatter 改写 ----------


def update_article_frontmatter(
    article_md_path: Path,
    new_status: str,
    today: str,
    new_thesis: str | None = None,
    new_target_platforms: list[str] | None = None,
    extra_log: str | None = None,
) -> None:
    """
    覆盖更新 ARTICLE.md：
      - frontmatter status / 可选 target_platforms
      - Thesis section（若 new_thesis 非空）
      - Status Log 追加一行
    """
    content = article_md_path.read_text(encoding="utf-8")

    # 改 frontmatter status
    content = re.sub(
        r"^status:\s*\S+\s*$",
        f"status: {new_status}",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    if new_target_platforms is not None:
        content = re.sub(
            r"^target_platforms:.*$",
            f"target_platforms: [{', '.join(new_target_platforms)}]",
            content,
            count=1,
            flags=re.MULTILINE,
        )

    # 替换 Thesis section 内容
    # heading 用 `[ \t]*\n` 精确匹配行尾，避免吃掉后续空行
    if new_thesis is not None:
        thesis_pattern = re.compile(
            r"(^##[ \t]+Thesis[ \t]*\n)(.*?)(?=^##[ \t]+|\Z)",
            re.MULTILINE | re.DOTALL,
        )

        def repl(m: re.Match) -> str:
            return m.group(1) + "\n" + new_thesis.strip() + "\n\n"

        content = thesis_pattern.sub(repl, content, count=1)

    # Status Log 追加
    if extra_log:
        log_line = f"- {today}: {extra_log}\n"
        # 在文件末尾追加（Status Log 是最后一节）
        if not content.endswith("\n"):
            content += "\n"
        content += log_line

    article_md_path.write_text(content, encoding="utf-8")


# ---------- STATE.md 改写 ----------


def find_active_section_bounds(lines: list[str]) -> tuple[int, int, int, int]:
    """返回 (section_start, section_end, sep_idx, data_start)"""
    section_start = None
    section_end = None
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m:
            if m.group(1).strip() == "Active Articles":
                section_start = i
            elif section_start is not None:
                section_end = i
                break
    if section_start is None:
        raise ValueError("'## Active Articles' heading not found")
    if section_end is None:
        section_end = len(lines)

    sep_idx = None
    for i in range(section_start + 1, section_end):
        if TABLE_SEP_RE.match(lines[i]):
            sep_idx = i
            break
    if sep_idx is None:
        raise ValueError("Active Articles 表缺少分隔行")
    data_start = sep_idx + 1
    return section_start, section_end, sep_idx, data_start


def find_completed_section_bounds(lines: list[str]) -> tuple[int, int, int, int]:
    section_start = None
    section_end = None
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m:
            if m.group(1).strip() == "Recently Completed":
                section_start = i
            elif section_start is not None:
                section_end = i
                break
    if section_start is None:
        raise ValueError("'## Recently Completed' heading not found")
    if section_end is None:
        section_end = len(lines)

    sep_idx = None
    for i in range(section_start + 1, section_end):
        if TABLE_SEP_RE.match(lines[i]):
            sep_idx = i
            break
    if sep_idx is None:
        raise ValueError("Recently Completed 表缺少分隔行")
    data_start = sep_idx + 1
    return section_start, section_end, sep_idx, data_start


def update_active_row(
    state_md_path: Path,
    slug: str,
    new_status: str,
    today: str,
    new_next_action: str,
) -> None:
    """改 Active Articles 表中 slug 对应行的 status / last_touched / next。
    不存在则抛 ValueError。
    """
    content = state_md_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    _, section_end, _, data_start = find_active_section_bounds(lines)

    found = False
    for i in range(data_start, section_end):
        if not TABLE_ROW_RE.match(lines[i]):
            break
        cells = [c.strip() for c in lines[i].strip("|").split("|")]
        if len(cells) >= 4 and cells[0] == slug:
            lines[i] = f"| {slug} | {new_status} | {today} | {new_next_action} |"
            found = True
            break
    if not found:
        raise ValueError(f"slug '{slug}' not in Active Articles table")

    new_content = "\n".join(lines)
    if content.endswith("\n"):
        new_content += "\n"
    state_md_path.write_text(new_content, encoding="utf-8")


def remove_from_active_and_add_to_completed(
    state_md_path: Path,
    slug: str,
    today: str,
    disposition: str,
    platforms_str: str,
) -> None:
    """从 Active 删行；在 Recently Completed 顶部插行（清理占位）。"""
    content = state_md_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    # remove from Active
    _, active_end, _, active_data_start = find_active_section_bounds(lines)
    keep_lines = []
    removed = False
    for i in range(active_data_start, active_end):
        if not TABLE_ROW_RE.match(lines[i]):
            keep_lines.append(lines[i])
            continue
        cells = [c.strip() for c in lines[i].strip("|").split("|")]
        if len(cells) >= 4 and cells[0] == slug:
            removed = True
            continue
        keep_lines.append(lines[i])
    if not removed:
        raise ValueError(f"slug '{slug}' not in Active Articles table")
    lines = lines[:active_data_start] + keep_lines + lines[active_end:]

    # add to Recently Completed (top, clean placeholders)
    _, comp_end, _, comp_data_start = find_completed_section_bounds(lines)
    new_row = f"| {slug} | {today} | {disposition} | {platforms_str} |"
    kept_data = []
    for i in range(comp_data_start, comp_end):
        if not TABLE_ROW_RE.match(lines[i]):
            kept_data.append(lines[i])
            continue
        cells = [c.strip() for c in lines[i].strip("|").split("|")]
        if any(PLACEHOLDER_RE.match(c) for c in cells):
            continue
        kept_data.append(lines[i])
    new_data = [new_row] + kept_data
    lines = lines[:comp_data_start] + new_data + lines[comp_end:]

    new_content = "\n".join(lines)
    if content.endswith("\n"):
        new_content += "\n"
    state_md_path.write_text(new_content, encoding="utf-8")


# ---------- 01-brief.md 渲染 ----------


def render_brief_md(slug: str, article_type: str, today: str, data: dict[str, Any]) -> str:
    def bullets(items: list[str]) -> str:
        if not items:
            return "_（无）_"
        return "\n".join(f"- {item}" for item in items)

    grill_block_lines = []
    for idx, qa in enumerate(data["grill_qa"], 1):
        grill_block_lines.append(f"### Q{idx}. {qa.get('q', '').strip()}\n")
        ua = (qa.get("user_answer") or "").strip()
        ar = (qa.get("ai_recommendation") or "").strip()
        fa = (qa.get("final") or "").strip()
        if ua:
            grill_block_lines.append(f"- **User**：{ua}")
        if ar:
            grill_block_lines.append(f"- **AI 建议**：{ar}")
        if fa:
            grill_block_lines.append(f"- **采纳**：{fa}")
        grill_block_lines.append("")
    grill_block = "\n".join(grill_block_lines).rstrip()

    align = data["alignment_check"]
    adr_list = ", ".join(align.get("adrs_consulted") or []) or "_（无）_"
    principles = ", ".join(align.get("principles_consulted") or []) or "_（无）_"
    conflicts = align.get("conflicts") or []
    conflict_block = (
        "无冲突，brief 与宪法对齐。"
        if not conflicts
        else "\n".join(f"- ⚠️ {c}" for c in conflicts)
    )
    notes = (align.get("notes") or "").strip() or "_（无）_"

    target_platforms = data.get("target_platforms") or []
    platforms_str = ", ".join(target_platforms) if target_platforms else "_（沿用 ARTICLE.md 原值）_"

    return f"""# 01-brief — {slug}

> 由 `/szw-discuss` 在 {today} 产出。
> Article type：`{article_type}`

## Thesis

{data["thesis"].strip()}

## Reader Payoff

{data["reader_payoff"].strip()}

## Supporting Claims

{bullets(data["supporting_claims"])}

## Counterargument

{data["counterargument"].strip()}

## Evidence Needed

{bullets(data["evidence_needed"])}

## Out of Scope

{bullets(data["out_of_scope"])}

## Target Platforms

{platforms_str}

---

## 附录 A：Topic Grill Q&A

{grill_block}

---

## 附录 B：宪法对齐检查

- **ADR 比对**：{adr_list}
- **Principles 比对**：{principles}

**冲突结论**：

{conflict_block}

**说明**：

{notes}
"""


# ---------- subcommands ----------


def cmd_commit(column_root: Path, slug: str) -> int:
    article_dir = column_root / ARTICLES_DIR / slug
    article_md = article_dir / "ARTICLE.md"
    if not article_md.exists():
        print(f"ERROR: ARTICLE.md not found: {article_md}", file=sys.stderr)
        return 2

    state_path = column_root / STATE_REL_PATH
    if not state_path.exists():
        print(f"ERROR: STATE.md not found: {state_path}", file=sys.stderr)
        return 3

    raw = sys.stdin.read()
    if not raw.strip():
        print("ERROR: stdin is empty; expected brief JSON", file=sys.stderr)
        return 4
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: stdin JSON parse failed: {e}", file=sys.stderr)
        return 4

    missing = REQUIRED_BRIEF_FIELDS - set(data.keys())
    if missing:
        print(
            f"ERROR: brief JSON missing fields: {sorted(missing)}",
            file=sys.stderr,
        )
        return 4

    if not isinstance(data["grill_qa"], list) or not data["grill_qa"]:
        print("ERROR: grill_qa must be a non-empty list", file=sys.stderr)
        return 4

    # 对齐检查 gate
    conflicts = data["alignment_check"].get("conflicts") or []
    if conflicts:
        print(
            "ERROR: alignment_check.conflicts is non-empty; "
            "use `abort` subcommand or revise brief to resolve:\n  - "
            + "\n  - ".join(conflicts),
            file=sys.stderr,
        )
        return 5

    # 读 ARTICLE.md type
    raw_article = article_md.read_text(encoding="utf-8")
    type_match = re.search(r"^type:\s*(\S+)\s*$", raw_article, re.MULTILINE)
    article_type = type_match.group(1) if type_match else "tech-blog"

    today = date.today().isoformat()
    brief_md = render_brief_md(slug, article_type, today, data)

    brief_path = article_dir / "01-brief.md"
    brief_path.write_text(brief_md, encoding="utf-8")

    update_article_frontmatter(
        article_md,
        new_status="brief_done",
        today=today,
        new_thesis=data["thesis"],
        new_target_platforms=data.get("target_platforms"),
        extra_log="brief_done via /szw-discuss",
    )

    try:
        update_active_row(
            state_path,
            slug=slug,
            new_status="brief_done",
            today=today,
            new_next_action="/szw-write",
        )
    except ValueError as e:
        print(f"ERROR: STATE.md update failed: {e}", file=sys.stderr)
        return 3

    print(f"✅ Committed brief for {slug}")
    print(f"   wrote: {brief_path.relative_to(column_root)}")
    print(f"   updated: {article_md.relative_to(column_root)} (status → brief_done)")
    print(f"   updated: STATE.md (Active row → brief_done)")
    print(f"\n👉 Next: /szw-write {slug}")
    return 0


def cmd_abort(column_root: Path, slug: str, reason: str) -> int:
    article_dir = column_root / ARTICLES_DIR / slug
    article_md = article_dir / "ARTICLE.md"
    if not article_md.exists():
        print(f"ERROR: ARTICLE.md not found: {article_md}", file=sys.stderr)
        return 2

    state_path = column_root / STATE_REL_PATH
    if not state_path.exists():
        print(f"ERROR: STATE.md not found: {state_path}", file=sys.stderr)
        return 3

    archived_dir = column_root / ARTICLES_DIR / ARCHIVED_SUBDIR / slug
    if archived_dir.exists():
        print(
            f"ERROR: archived target already exists: {archived_dir}",
            file=sys.stderr,
        )
        return 6

    today = date.today().isoformat()

    # 读 ARTICLE.md 拿 platforms（用于 Recently Completed 行）
    raw_article = article_md.read_text(encoding="utf-8")
    pf_match = re.search(r"^target_platforms:\s*\[(.*?)\]\s*$", raw_article, re.MULTILINE)
    platforms_str = pf_match.group(1).strip() if pf_match else "-"

    # 写 abort 原因到 ARTICLE.md
    update_article_frontmatter(
        article_md,
        new_status="archived",
        today=today,
        extra_log=f"archived via /szw-discuss — abort reason: {reason}",
    )

    # 移动到 archived/
    archived_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(article_dir), str(archived_dir))

    # 更新 STATE.md
    try:
        remove_from_active_and_add_to_completed(
            state_path,
            slug=slug,
            today=today,
            disposition="archived",
            platforms_str=platforms_str or "-",
        )
    except ValueError as e:
        print(f"ERROR: STATE.md update failed: {e}", file=sys.stderr)
        return 3

    print(f"⚠️ Aborted {slug}")
    print(f"   moved: articles/{slug}/ → articles/archived/{slug}/")
    print(f"   reason: {reason}")
    print(f"   updated: STATE.md (Active → Recently Completed, archived)")
    return 0


# ---------- main ----------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Finalize szw-discuss")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_commit = sub.add_parser("commit", help="Render brief + advance status")
    p_commit.add_argument("--slug", required=True)

    p_abort = sub.add_parser("abort", help="Move article to archived/")
    p_abort.add_argument("--slug", required=True)
    p_abort.add_argument("--reason", required=True)

    args = parser.parse_args(argv[1:])

    try:
        column_root = find_column_root(Path.cwd())
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if args.cmd == "commit":
        return cmd_commit(column_root, args.slug)
    if args.cmd == "abort":
        return cmd_abort(column_root, args.slug, args.reason)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
