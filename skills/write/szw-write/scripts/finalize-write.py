#!/usr/bin/env python3
"""
finalize-write.py — Phase 3：把 draft / polish 内容落盘 + history 快照 + 推进状态

子命令:
  commit --slug <slug>     # 从 stdin 读 JSON，写 04-draft.md（full 或 section 替换）+ history 快照 + 可选状态推进

stdin JSON schema（参考 references/write-schema.md）:
  {
    "mode": "draft" | "polish" | "both",
    "target": "full" | "S<n>",          // section ID 形式如 "S2"
    "content": "the markdown to save",
    "diff_summary": "tightened §2 reader payoff; removed 或许 x3",
    "sections_changed": ["S2"],          // 自报；INDEX 记录用
    "advance_status_to": "draft_done" | null   // 显式 override；null/缺失 → 脚本按规则自动决定
  }

规则：
  - target=full：04-draft.md 整文件覆盖（首次起稿创建）
  - target=S<n>：04-draft.md 必须存在；找 ## §<n>. <title> 节，整段替换（含 heading）；content 必须包含 heading
  - 自动 status 推进：target=full + mode in {draft, both} + current_status ∈ {brief_done, research_done, outline_done} → draft_done
                     其他场景默认不动 status
  - advance_status_to 可显式覆盖；只允许设为 "draft_done" 或 null
  - 每次 commit 写一份快照到 .zero/writing-history/<slug>/NN-<mode>-<target>-<ts>.md（NN 自增）
  - INDEX.md 不存在则创建，存在则在表头部插入新行

退出码:
  0  成功
  1  不在专栏目录
  2  slug / ARTICLE.md 不存在
  3  STATE.md 缺失 / 解析失败
  4  stdin JSON 缺字段 / 字段值非法
  5  section 替换失败：04-draft.md 不存在 / 找不到 ## §<n> 节 / content 缺 heading
  6  advance_status_to 非法转移
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

CONFIG_REL_PATH = ".zero/szw-config.json"
STATE_REL_PATH = ".zero/STATE.md"
ARTICLES_DIR = "articles"
WRITING_HISTORY_DIR = ".zero/writing-history"

PLACEHOLDER_RE = re.compile(r"^<.*>$")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|$")
HEADING_RE = re.compile(r"^##\s+(.+)$")
SECTION_ID_RE = re.compile(r"^S(\d+)$")
SNAPSHOT_NN_RE = re.compile(r"^(\d+)-")

VALID_MODES = {"draft", "polish", "both"}
VALID_ADVANCE = {"draft_done", None}
ADVANCEABLE_FROM = {"brief_done", "research_done", "outline_done"}

REQUIRED_TOP_FIELDS = {"mode", "target", "content", "diff_summary", "sections_changed"}


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


def get_article_status(article_md_path: Path) -> str | None:
    content = article_md_path.read_text(encoding="utf-8")
    m = re.search(r"^status:\s*(\S+)\s*$", content, re.MULTILINE)
    return m.group(1) if m else None


def update_article_frontmatter(
    article_md_path: Path,
    new_status: str | None,
    today: str,
    extra_log: str,
) -> None:
    content = article_md_path.read_text(encoding="utf-8")
    if new_status is not None:
        content = re.sub(
            r"^status:\s*\S+\s*$",
            f"status: {new_status}",
            content,
            count=1,
            flags=re.MULTILINE,
        )
    log_line = f"- {today}: {extra_log}\n"
    if not content.endswith("\n"):
        content += "\n"
    content += log_line
    article_md_path.write_text(content, encoding="utf-8")


# ---------- STATE.md 改写 ----------


def find_active_section_bounds(lines: list[str]) -> tuple[int, int, int]:
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
    return section_end, sep_idx, sep_idx + 1


def update_active_row(
    state_md_path: Path,
    slug: str,
    new_status: str | None,
    today: str,
    new_next_action: str | None,
) -> None:
    """new_status / new_next_action 为 None 表示不修改对应字段"""
    content = state_md_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    section_end, _, data_start = find_active_section_bounds(lines)
    found = False
    for i in range(data_start, section_end):
        if not TABLE_ROW_RE.match(lines[i]):
            break
        cells = [c.strip() for c in lines[i].strip("|").split("|")]
        if len(cells) >= 4 and cells[0] == slug:
            status = new_status if new_status is not None else cells[1]
            next_action = new_next_action if new_next_action is not None else cells[3]
            lines[i] = f"| {slug} | {status} | {today} | {next_action} |"
            found = True
            break
    if not found:
        raise ValueError(f"slug '{slug}' not in Active Articles table")
    new_content = "\n".join(lines)
    if content.endswith("\n"):
        new_content += "\n"
    state_md_path.write_text(new_content, encoding="utf-8")


# ---------- section 替换 ----------


def replace_section(content: str, n: int, new_block: str) -> tuple[bool, str]:
    r"""
    在 content 里找 ^## §<n>[\.\s] 节，整段（含 heading）替换为 new_block。
    返回 (success, new_content)。new_block 必须以 ## §<n> 开头。
    """
    pattern = re.compile(
        r"^(##[ \t]+§"
        + str(n)
        + r"[\.\s][^\n]*\n.*?)(?=^##[ \t]+§\d+[\.\s]|^##[ \t]+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(content)
    if not m:
        return False, content
    # new_block 末尾确保有换行（保持下一段间距）
    if not new_block.endswith("\n"):
        new_block = new_block + "\n"
    if not new_block.endswith("\n\n"):
        new_block = new_block + "\n"
    new_content = content[: m.start()] + new_block + content[m.end() :]
    return True, new_content


def section_id_to_n(section_id: str) -> int | None:
    m = SECTION_ID_RE.match(section_id)
    return int(m.group(1)) if m else None


# ---------- writing history ----------


def next_snapshot_nn(slug_history_dir: Path) -> int:
    if not slug_history_dir.exists():
        return 1
    max_nn = 0
    for f in slug_history_dir.iterdir():
        if not f.is_file() or f.name == "INDEX.md":
            continue
        m = SNAPSHOT_NN_RE.match(f.name)
        if m:
            max_nn = max(max_nn, int(m.group(1)))
    return max_nn + 1


def write_snapshot(
    slug_history_dir: Path,
    nn: int,
    mode: str,
    target: str,
    timestamp: str,
    content: str,
    diff_summary: str,
    sections_changed: list[str],
) -> Path:
    slug_history_dir.mkdir(parents=True, exist_ok=True)
    safe_target = target.replace("/", "-")
    fname = f"{nn:02d}-{mode}-{safe_target}-{timestamp}.md"
    snap_path = slug_history_dir / fname

    sections_str = ", ".join(sections_changed) if sections_changed else "_（未声明）_"
    header = f"""<!--
mode: {mode}
target: {target}
timestamp: {timestamp}
sections_changed: {sections_str}
diff_summary: {diff_summary}
-->

"""
    snap_path.write_text(header + content, encoding="utf-8")
    return snap_path


def update_history_index(
    slug_history_dir: Path,
    slug: str,
    nn: int,
    when_human: str,
    mode: str,
    target: str,
    sections_changed: list[str],
    diff_summary: str,
) -> None:
    index_path = slug_history_dir / "INDEX.md"
    sections_str = ", ".join(sections_changed) if sections_changed else "—"
    new_row = (
        f"| {nn:02d} | {when_human} | {mode} | {target} | {sections_str} | {diff_summary} |"
    )

    if not index_path.exists():
        content = f"""# Writing History — {slug}

> Auto-maintained by `/szw-write`. Latest first.

| # | When | Mode | Target | Sections | Diff summary |
|---|---|---|---|---|---|
{new_row}
"""
        index_path.write_text(content, encoding="utf-8")
        return

    content = index_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    # 找表分隔行，新行插在分隔行之后第一行
    sep_idx = None
    for i, line in enumerate(lines):
        if TABLE_SEP_RE.match(line):
            sep_idx = i
            break
    if sep_idx is None:
        # 表损坏，追加到末尾
        if not content.endswith("\n"):
            content += "\n"
        content += new_row + "\n"
        index_path.write_text(content, encoding="utf-8")
        return
    new_lines = lines[: sep_idx + 1] + [new_row] + lines[sep_idx + 1 :]
    new_content = "\n".join(new_lines)
    if content.endswith("\n"):
        new_content += "\n"
    index_path.write_text(new_content, encoding="utf-8")


# ---------- JSON 校验 ----------


def validate_payload(data: dict[str, Any]) -> tuple[bool, str]:
    missing = REQUIRED_TOP_FIELDS - set(data.keys())
    if missing:
        return False, f"missing top fields: {sorted(missing)}"
    if data["mode"] not in VALID_MODES:
        return False, f"mode must be one of {sorted(VALID_MODES)}; got {data['mode']!r}"
    target = data["target"]
    if target != "full" and not SECTION_ID_RE.match(target):
        return False, f"target must be 'full' or 'S<n>'; got {target!r}"
    if not isinstance(data["content"], str) or not data["content"].strip():
        return False, "content must be non-empty string"
    if not isinstance(data["diff_summary"], str) or not data["diff_summary"].strip():
        return False, "diff_summary must be non-empty string"
    if not isinstance(data["sections_changed"], list):
        return False, "sections_changed must be list"
    advance = data.get("advance_status_to")
    if advance not in VALID_ADVANCE:
        return False, (
            f"advance_status_to must be 'draft_done' or null; got {advance!r}"
        )
    return True, ""


# ---------- status 推进决策 ----------


def decide_status_advance(
    current_status: str | None,
    target: str,
    mode: str,
    explicit: str | None,
) -> tuple[str | None, str]:
    """
    返回 (new_status_or_None, 推理说明)。new_status=None 表示不动。
    explicit 优先；否则按规则自动决定。
    """
    if explicit is not None:
        # 校验显式值合法
        if current_status not in ADVANCEABLE_FROM and explicit == "draft_done":
            return None, (
                f"explicit advance_status_to='draft_done' rejected: "
                f"current_status='{current_status}' not in {sorted(ADVANCEABLE_FROM)}"
            )
        return explicit, "explicit override accepted"

    # 自动规则
    if (
        target == "full"
        and mode in {"draft", "both"}
        and current_status in ADVANCEABLE_FROM
    ):
        return "draft_done", f"auto: full + {mode} from {current_status} → draft_done"

    return None, f"auto: keep status='{current_status}' (no advance trigger matched)"


# ---------- commit ----------


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
        print("ERROR: stdin is empty; expected write JSON", file=sys.stderr)
        return 4
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: stdin JSON parse failed: {e}", file=sys.stderr)
        return 4

    ok, msg = validate_payload(data)
    if not ok:
        print(f"ERROR: {msg}", file=sys.stderr)
        return 4

    mode = data["mode"]
    target = data["target"]
    content = data["content"]
    diff_summary = data["diff_summary"].strip()
    sections_changed = data["sections_changed"]
    explicit_advance = data.get("advance_status_to")

    draft_md = article_dir / "04-draft.md"

    # 写 04-draft.md
    if target == "full":
        # 全文覆盖
        draft_md.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
    else:
        # section 替换
        n = section_id_to_n(target)
        if n is None:
            print(f"ERROR: invalid section target {target!r}", file=sys.stderr)
            return 5
        if not draft_md.exists():
            print(
                f"ERROR: section mode requires existing 04-draft.md "
                f"(not found: {draft_md.relative_to(column_root)}). "
                "Use target='full' for first draft.",
                file=sys.stderr,
            )
            return 5
        # content 必须以 ## §<n> 开头
        head_re = re.compile(
            r"^##[ \t]+§" + str(n) + r"[\.\s]", re.MULTILINE
        )
        if not head_re.match(content.strip().splitlines()[0] if content.strip() else ""):
            print(
                f"ERROR: section content must start with '## §{n}.' or '## §{n} ' heading. "
                "(Submitting body-only is not supported; include the heading line.)",
                file=sys.stderr,
            )
            return 5
        existing = draft_md.read_text(encoding="utf-8")
        success, new_doc = replace_section(existing, n, content)
        if not success:
            print(
                f"ERROR: failed to find existing section §{n} in 04-draft.md. "
                "Use target='full' to write/rewrite the whole article first.",
                file=sys.stderr,
            )
            return 5
        draft_md.write_text(new_doc, encoding="utf-8")

    # status 推进
    today = date.today().isoformat()
    current_status = get_article_status(article_md)
    new_status, advance_reason = decide_status_advance(
        current_status, target, mode, explicit_advance
    )
    if new_status is None and explicit_advance is not None:
        # 显式指定但拒绝
        print(f"ERROR: {advance_reason}", file=sys.stderr)
        return 6

    # ARTICLE.md 更新
    log_target = "full" if target == "full" else target
    log_msg = (
        f"draft_done via /szw-write (mode={mode}, target={log_target})"
        if new_status == "draft_done"
        else f"write iteration via /szw-write (mode={mode}, target={log_target}; "
        f"status unchanged={current_status})"
    )
    update_article_frontmatter(article_md, new_status, today, log_msg)

    # STATE.md 更新
    state_next_action = (
        "/szw-review" if new_status == "draft_done" else None
    )
    state_status_to_set = new_status  # None = 不动 status，仅刷 last_touched
    try:
        update_active_row(
            state_path,
            slug=slug,
            new_status=state_status_to_set,
            today=today,
            new_next_action=state_next_action,
        )
    except ValueError as e:
        print(f"ERROR: STATE.md update failed: {e}", file=sys.stderr)
        return 3

    # writing history
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M")
    when_human = datetime.now().strftime("%Y-%m-%d %H:%M")
    slug_hist_dir = column_root / WRITING_HISTORY_DIR / slug
    nn = next_snapshot_nn(slug_hist_dir)
    snap_path = write_snapshot(
        slug_hist_dir,
        nn=nn,
        mode=mode,
        target=target,
        timestamp=timestamp,
        content=content,
        diff_summary=diff_summary,
        sections_changed=sections_changed,
    )
    update_history_index(
        slug_hist_dir,
        slug=slug,
        nn=nn,
        when_human=when_human,
        mode=mode,
        target=target,
        sections_changed=sections_changed,
        diff_summary=diff_summary,
    )

    # 输出
    print(f"✅ Committed write for {slug}")
    print(f"   mode: {mode} · target: {target}")
    print(f"   wrote: {draft_md.relative_to(column_root)}")
    print(f"   snapshot: {snap_path.relative_to(column_root)} (#{nn:02d})")
    print(f"   updated: {article_md.relative_to(column_root)}")
    if new_status:
        print(f"   status: {current_status} → {new_status}")
    else:
        print(f"   status: {current_status} (unchanged) — {advance_reason}")
    print(f"   STATE.md: row updated (last_touched={today})")

    if new_status == "draft_done":
        print(f"\n👉 Next: /szw-review {slug}")
    elif current_status == "review_failed":
        print(f"\n👉 Next: /szw-review {slug} (re-run after polish)")
    else:
        print(f"\n👉 Next: continue writing or /szw-review {slug}")

    return 0


# ---------- main ----------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Finalize szw-write")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_commit = sub.add_parser("commit", help="Save draft + snapshot history + advance status")
    p_commit.add_argument("--slug", required=True)
    args = parser.parse_args(argv[1:])

    try:
        column_root = find_column_root(Path.cwd())
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if args.cmd == "commit":
        return cmd_commit(column_root, args.slug)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
