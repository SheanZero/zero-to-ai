#!/usr/bin/env python3
"""
finalize-outline.py — Phase 3：把 thesis map + section slices 落盘 + 推进状态

子命令:
  commit --slug <slug>     # 从 stdin 读 JSON，渲染 03-outline.md，更新 ARTICLE.md / STATE.md

stdin JSON schema（参考 references/outline-schema.md）:
  {
    "thesis_map": {
      "main_thesis": "...",
      "supporting": [
        {"claim_id": "C1", "claim_text": "...", "evidence_ref": "...", "argument_link": "..."}
      ],
      "counter": [
        {"text": "...", "response": "..."}
      ],
      "argument_chain_ok": true,
      "argument_chain_notes": "..."
    },
    "section_slices": [
      {
        "n": 1,
        "title": "...",
        "core_claim": "C1 + C2",
        "evidence_needed": "...",
        "reader_payoff": "...",
        "programmer_implication": "...",
        "counterargument": "...",
        "acceptance_criteria": ["AC1: ...", "AC2: ..."]
      }
    ],
    "decision_log": [
      {"round": 1, "phase": "thesis_map", "decision": "...", "reason": "..."}
    ],
    "loop_rounds": 0,
    "verdict": "passed" | "weak_section_unresolved",
    "weak_section_notes": ""
  }

退出码:
  0  成功
  1  不在专栏目录
  2  slug / ARTICLE.md 不存在
  3  STATE.md 缺失 / 解析失败
  4  stdin JSON 缺字段 / 解析失败
  5  verdict != 'passed'（拒绝 commit；让 AI escalate 回 /szw-research 或 /szw-discuss）
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

CONFIG_REL_PATH = ".zero/szw-config.json"
STATE_REL_PATH = ".zero/STATE.md"
ARTICLES_DIR = "articles"

PLACEHOLDER_RE = re.compile(r"^<.*>$")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|$")
HEADING_RE = re.compile(r"^##\s+(.+)$")

REQUIRED_TOP_FIELDS = {
    "thesis_map",
    "section_slices",
    "decision_log",
    "loop_rounds",
    "verdict",
}
REQUIRED_THESIS_MAP_FIELDS = {"main_thesis", "supporting", "counter", "argument_chain_ok"}
REQUIRED_SLICE_FIELDS = {
    "n",
    "title",
    "core_claim",
    "evidence_needed",
    "reader_payoff",
    "programmer_implication",
    "counterargument",
    "acceptance_criteria",
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


# ---------- ARTICLE.md 改写 ----------


def update_article_frontmatter(
    article_md_path: Path,
    new_status: str,
    today: str,
    extra_log: str,
) -> None:
    content = article_md_path.read_text(encoding="utf-8")
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
    new_status: str,
    today: str,
    new_next_action: str,
) -> None:
    content = state_md_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    section_end, _, data_start = find_active_section_bounds(lines)
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


# ---------- 03-outline.md 渲染 ----------


def render_outline_md(slug: str, today: str, mode: str, data: dict[str, Any]) -> str:
    tm = data["thesis_map"]
    slices = data["section_slices"]
    decisions = data["decision_log"]

    # §1 thesis map
    sup_lines = []
    for i, s in enumerate(tm["supporting"], 1):
        cid = s.get("claim_id", "?")
        ctext = s.get("claim_text", "").strip()
        ev = (s.get("evidence_ref") or "").strip() or "_（未引用证据）_"
        link = (s.get("argument_link") or "").strip() or "_（未填论证链）_"
        sup_lines.append(
            f"#### S{i} · {cid}\n"
            f"- **Claim**：{ctext}\n"
            f"- **Evidence ref**：{ev}\n"
            f"- **Argument link**：{link}"
        )
    sup_block = "\n\n".join(sup_lines) if sup_lines else "_（无）_"

    counter_lines = []
    for i, c in enumerate(tm["counter"], 1):
        text = (c.get("text") or "").strip()
        resp = (c.get("response") or "").strip()
        counter_lines.append(
            f"#### Counter {i}\n- **声音**：{text}\n- **回应**：{resp}"
        )
    counter_block = "\n\n".join(counter_lines) if counter_lines else "_（无）_"

    chain_ok = "✅ 通过" if tm.get("argument_chain_ok") else "⚠️ 不通过"
    chain_notes = (tm.get("argument_chain_notes") or "").strip() or "_（无）_"

    # §2 section slices
    slice_lines = []
    for s in slices:
        n = s["n"]
        ac_block = "\n".join(f"  - {ac}" for ac in s["acceptance_criteria"])
        slice_lines.append(
            f"### §{n}. {s['title']}\n\n"
            f"- **Core claim**：{s['core_claim']}\n"
            f"- **Evidence needed**：{s['evidence_needed']}\n"
            f"- **Reader payoff**：{s['reader_payoff']}\n"
            f"- **Programmer implication**：{s['programmer_implication']}\n"
            f"- **Counterargument**：{s['counterargument']}\n"
            f"- **Acceptance criteria**：\n{ac_block}"
        )
    slices_block = "\n\n".join(slice_lines) if slice_lines else "_（无）_"

    # §3 decision log
    if decisions:
        dec_lines = []
        for d in decisions:
            dec_lines.append(
                f"- **Round {d.get('round', '?')}** "
                f"({d.get('phase', '')})：{d.get('decision', '')} "
                f"— _{d.get('reason', '')}_"
            )
        decisions_block = "\n".join(dec_lines)
    else:
        decisions_block = "_（无内部循环；首轮即通过）_"

    loop_rounds = data.get("loop_rounds", 0)
    verdict = data.get("verdict", "passed")

    mode_note = (
        "基于 01-brief.md + 02-research.md（v2.0 完整路径）"
        if mode == "brief_plus_research"
        else "⚠️ 基于 01-brief.md only（02-research.md 缺失；evidence 未独立验证）"
    )

    return f"""# 03-outline — {slug}

> 由 `/szw-outline` 在 {today} 产出。
> 模式：{mode_note}
> 内部循环：{loop_rounds} 轮 · 结论：`{verdict}`

## §1 Thesis Map

### Main Thesis

{tm["main_thesis"].strip()}

### Supporting

{sup_block}

### Counter

{counter_block}

### Argument Chain

**结论**：{chain_ok}

**说明**：{chain_notes}

---

## §2 Section Slices

{slices_block}

---

## §3 Decision Log

{decisions_block}
"""


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
        print("ERROR: stdin is empty; expected outline JSON", file=sys.stderr)
        return 4
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: stdin JSON parse failed: {e}", file=sys.stderr)
        return 4

    missing_top = REQUIRED_TOP_FIELDS - set(data.keys())
    if missing_top:
        print(
            f"ERROR: outline JSON missing top fields: {sorted(missing_top)}",
            file=sys.stderr,
        )
        return 4

    tm = data["thesis_map"]
    if not isinstance(tm, dict):
        print("ERROR: thesis_map must be an object", file=sys.stderr)
        return 4
    missing_tm = REQUIRED_THESIS_MAP_FIELDS - set(tm.keys())
    if missing_tm:
        print(
            f"ERROR: thesis_map missing fields: {sorted(missing_tm)}",
            file=sys.stderr,
        )
        return 4
    if not isinstance(tm.get("supporting"), list) or not tm["supporting"]:
        print("ERROR: thesis_map.supporting must be non-empty list", file=sys.stderr)
        return 4
    if not isinstance(tm.get("counter"), list):
        print("ERROR: thesis_map.counter must be a list", file=sys.stderr)
        return 4

    slices = data["section_slices"]
    if not isinstance(slices, list) or not slices:
        print("ERROR: section_slices must be non-empty list", file=sys.stderr)
        return 4
    n_slices = len(slices)
    if n_slices < 3 or n_slices > 8:
        print(
            f"WARN: section_slices count = {n_slices}; recommended 4-6 strong sections.",
            file=sys.stderr,
        )
    for i, s in enumerate(slices):
        if not isinstance(s, dict):
            print(f"ERROR: section_slices[{i}] must be object", file=sys.stderr)
            return 4
        missing = REQUIRED_SLICE_FIELDS - set(s.keys())
        if missing:
            print(
                f"ERROR: section_slices[{i}] missing fields: {sorted(missing)}",
                file=sys.stderr,
            )
            return 4
        if not isinstance(s["acceptance_criteria"], list) or not s["acceptance_criteria"]:
            print(
                f"ERROR: section_slices[{i}].acceptance_criteria must be non-empty list",
                file=sys.stderr,
            )
            return 4

    # verdict gate —— 弱 section 阻断 commit
    verdict = data.get("verdict", "")
    if verdict != "passed":
        notes = data.get("weak_section_notes", "") or "(no notes)"
        print(
            f"ERROR: verdict='{verdict}' (not 'passed'). Outline rejected.\n"
            f"  notes: {notes}\n"
            "  Action: AI should ask user to escalate — back to /szw-research "
            "for more evidence, or /szw-discuss to revise the thesis.",
            file=sys.stderr,
        )
        return 5

    # mode 推断（看 02-research.md 是否存在）
    research_md = article_dir / "02-research.md"
    mode = "brief_plus_research" if research_md.exists() else "brief_only"

    today = date.today().isoformat()
    outline_md = render_outline_md(slug, today, mode, data)

    outline_path = article_dir / "03-outline.md"
    outline_path.write_text(outline_md, encoding="utf-8")

    update_article_frontmatter(
        article_md,
        new_status="outline_done",
        today=today,
        extra_log="outline_done via /szw-outline",
    )

    try:
        update_active_row(
            state_path,
            slug=slug,
            new_status="outline_done",
            today=today,
            new_next_action="/szw-write",
        )
    except ValueError as e:
        print(f"ERROR: STATE.md update failed: {e}", file=sys.stderr)
        return 3

    print(f"✅ Committed outline for {slug}")
    print(f"   wrote: {outline_path.relative_to(column_root)}")
    print(f"   updated: {article_md.relative_to(column_root)} (status → outline_done)")
    print(f"   updated: STATE.md (Active row → outline_done)")
    print(f"   mode: {mode} · slices: {n_slices} · loops: {data.get('loop_rounds', 0)}")
    print(f"\n👉 Next: /szw-write {slug}")
    return 0


# ---------- main ----------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Finalize szw-outline")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_commit = sub.add_parser("commit", help="Render outline + advance status")
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
