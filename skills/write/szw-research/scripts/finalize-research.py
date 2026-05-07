#!/usr/bin/env python3
"""
finalize-research.py — Phase 3：把 evidence + diagnosis 落盘 + 推进状态

子命令:
  commit --slug <slug>     # 从 stdin 读 JSON，渲染 02-research.md，更新 ARTICLE.md / STATE.md，同步 .zero/evidence/<topic>.md

stdin JSON schema（参考 references/research-schema.md）:
  {
    "evidence_cards": [
      {
        "claim_id": "C1",
        "claim_text": "...",
        "status": "covered" | "source_needed" | "weak",
        "sources": [
          {"type": "official-doc|paper|blog|community|...", "title": "...", "date": "...",
           "url": "...", "quote": "...", "confidence": "high|medium|low"}
        ]
      }
    ],
    "claim_diagnosis": [
      {
        "claim_id": "C1",
        "claim_text": "...",
        "type": "fact|interpretation|opinion|prediction|advice",
        "evidence_required": "...",
        "evidence_available": "...",
        "counter_evidence": "...",
        "confidence": "high|medium|low",
        "risk": "L|M|H",
        "safer_rewrite": "..."
      }
    ],
    "overall_credibility": "high|medium|low",
    "high_risk_claims": ["C1"],          // 子集 of claim_diagnosis[].claim_id where risk='H'
    "loop_rounds": 0,                    // Phase1↔Phase2 内部循环次数（0/1/2）
    "verdict": "passed" | "passed_with_high_risk" | "needs_rework",
    "user_decision": "accept" | "downgrade" | null,  // 仅 verdict=passed_with_high_risk 时必填
    "recommended_actions": ["..."],
    "notes": "...",
    "evidence_bank_writes": [             // 可选；同步到 .zero/evidence/<topic>.md
      {"topic": "claude-code-skills",
       "sources": [{"title":"...","url":"...","quote":"...","confidence":"high","from_claim":"C1"}]}
    ]
  }

退出码:
  0  成功
  1  不在专栏目录
  2  slug / ARTICLE.md / 01-brief.md 不存在
  3  STATE.md 缺失 / 解析失败
  4  stdin JSON 缺字段 / 解析失败 / 字段值非法
  5  verdict gate：
       - verdict=needs_rework
       - verdict=passed_with_high_risk + user_decision != "accept"
       - verdict=passed + high_risk_claims 非空（自相矛盾）
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
EVIDENCE_DIR = ".zero/evidence"

PLACEHOLDER_RE = re.compile(r"^<.*>$")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|$")
HEADING_RE = re.compile(r"^##\s+(.+)$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

REQUIRED_TOP_FIELDS = {
    "evidence_cards",
    "claim_diagnosis",
    "overall_credibility",
    "high_risk_claims",
    "loop_rounds",
    "verdict",
}
REQUIRED_CARD_FIELDS = {"claim_id", "claim_text", "status", "sources"}
REQUIRED_SOURCE_FIELDS = {"type", "title", "url", "quote", "confidence"}
REQUIRED_DIAG_FIELDS = {
    "claim_id",
    "claim_text",
    "type",
    "evidence_required",
    "evidence_available",
    "confidence",
    "risk",
    "safer_rewrite",
}

VALID_CARD_STATUS = {"covered", "source_needed", "weak"}
VALID_CONFIDENCE = {"high", "medium", "low"}
VALID_RISK = {"L", "M", "H"}
VALID_CLAIM_TYPE = {"fact", "interpretation", "opinion", "prediction", "advice"}
VALID_VERDICT = {"passed", "passed_with_high_risk", "needs_rework"}


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


# ---------- ARTICLE.md 改写（与 outline / discuss 同模式） ----------


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


# ---------- JSON 校验 ----------


def validate_payload(data: dict[str, Any]) -> tuple[bool, str]:
    missing = REQUIRED_TOP_FIELDS - set(data.keys())
    if missing:
        return False, f"missing top fields: {sorted(missing)}"

    if data["overall_credibility"] not in VALID_CONFIDENCE:
        return False, f"overall_credibility must be one of {sorted(VALID_CONFIDENCE)}"
    if data["verdict"] not in VALID_VERDICT:
        return False, f"verdict must be one of {sorted(VALID_VERDICT)}"

    if not isinstance(data["evidence_cards"], list):
        return False, "evidence_cards must be list"
    if not isinstance(data["claim_diagnosis"], list) or not data["claim_diagnosis"]:
        return False, "claim_diagnosis must be non-empty list"
    if not isinstance(data["high_risk_claims"], list):
        return False, "high_risk_claims must be list"
    if not isinstance(data["loop_rounds"], int) or data["loop_rounds"] < 0:
        return False, "loop_rounds must be non-negative int"

    # cards 校验
    for i, card in enumerate(data["evidence_cards"]):
        if not isinstance(card, dict):
            return False, f"evidence_cards[{i}] must be object"
        miss = REQUIRED_CARD_FIELDS - set(card.keys())
        if miss:
            return False, f"evidence_cards[{i}] missing fields: {sorted(miss)}"
        if card["status"] not in VALID_CARD_STATUS:
            return False, (
                f"evidence_cards[{i}].status must be one of {sorted(VALID_CARD_STATUS)}"
            )
        if not isinstance(card["sources"], list):
            return False, f"evidence_cards[{i}].sources must be list"
        for j, src in enumerate(card["sources"]):
            if not isinstance(src, dict):
                return False, f"evidence_cards[{i}].sources[{j}] must be object"
            sm = REQUIRED_SOURCE_FIELDS - set(src.keys())
            if sm:
                return False, (
                    f"evidence_cards[{i}].sources[{j}] missing fields: {sorted(sm)}"
                )
            if src["confidence"] not in VALID_CONFIDENCE:
                return False, (
                    f"evidence_cards[{i}].sources[{j}].confidence must be one of "
                    f"{sorted(VALID_CONFIDENCE)}"
                )

    # diagnosis 校验
    diag_claim_ids = set()
    high_risk_actual = set()
    for i, d in enumerate(data["claim_diagnosis"]):
        if not isinstance(d, dict):
            return False, f"claim_diagnosis[{i}] must be object"
        miss = REQUIRED_DIAG_FIELDS - set(d.keys())
        if miss:
            return False, f"claim_diagnosis[{i}] missing fields: {sorted(miss)}"
        if d["type"] not in VALID_CLAIM_TYPE:
            return False, (
                f"claim_diagnosis[{i}].type must be one of {sorted(VALID_CLAIM_TYPE)}"
            )
        if d["confidence"] not in VALID_CONFIDENCE:
            return False, (
                f"claim_diagnosis[{i}].confidence must be one of {sorted(VALID_CONFIDENCE)}"
            )
        if d["risk"] not in VALID_RISK:
            return False, (
                f"claim_diagnosis[{i}].risk must be one of {sorted(VALID_RISK)}"
            )
        diag_claim_ids.add(d["claim_id"])
        if d["risk"] == "H":
            high_risk_actual.add(d["claim_id"])

    # high_risk_claims 一致性
    declared = set(data["high_risk_claims"])
    if declared != high_risk_actual:
        return False, (
            f"high_risk_claims {sorted(declared)} mismatch claims with risk='H' in diagnosis: "
            f"{sorted(high_risk_actual)}"
        )

    # evidence bank writes（可选）
    bank = data.get("evidence_bank_writes")
    if bank is not None:
        if not isinstance(bank, list):
            return False, "evidence_bank_writes must be list"
        for i, b in enumerate(bank):
            if not isinstance(b, dict):
                return False, f"evidence_bank_writes[{i}] must be object"
            if "topic" not in b or "sources" not in b:
                return False, (
                    f"evidence_bank_writes[{i}] needs 'topic' and 'sources'"
                )
            topic = b["topic"]
            if not isinstance(topic, str) or not SLUG_RE.match(topic):
                return False, (
                    f"evidence_bank_writes[{i}].topic invalid (must match {SLUG_RE.pattern}): "
                    f"{topic!r}"
                )
            if not isinstance(b["sources"], list) or not b["sources"]:
                return False, (
                    f"evidence_bank_writes[{i}].sources must be non-empty list"
                )

    return True, ""


def check_verdict_gate(data: dict[str, Any]) -> tuple[bool, str]:
    """返回 (允许 commit, 错误信息)。错误信息非空时拒绝 commit。"""
    verdict = data["verdict"]
    high_risk = data["high_risk_claims"]
    user_decision = data.get("user_decision")

    if verdict == "needs_rework":
        return False, (
            "verdict='needs_rework'. Internal loop exhausted (loop_rounds="
            f"{data['loop_rounds']}). Action: AI should escalate — back to /szw-discuss "
            "to revise thesis, or run another /szw-research round manually with new evidence."
        )

    if verdict == "passed":
        if high_risk:
            return False, (
                f"verdict='passed' but high_risk_claims = {sorted(high_risk)} (non-empty). "
                "Self-contradictory. If user accepts the high risk, set verdict='passed_with_high_risk' "
                "+ user_decision='accept'. If not, escalate."
            )
        return True, ""

    if verdict == "passed_with_high_risk":
        if not high_risk:
            return False, (
                "verdict='passed_with_high_risk' but high_risk_claims is empty. "
                "Use verdict='passed' instead."
            )
        if user_decision == "accept":
            return True, ""
        if user_decision == "downgrade":
            return False, (
                f"verdict='passed_with_high_risk', user_decision='downgrade'. "
                f"HIGH-risk claims: {sorted(high_risk)}. "
                "Action: AI should advise user to run /szw-discuss <slug> to revise brief "
                "(soften thesis or drop the high-risk claims)."
            )
        return False, (
            "verdict='passed_with_high_risk' requires user_decision='accept' or 'downgrade'. "
            f"Got: {user_decision!r}. Ask user to choose."
        )

    return False, f"unhandled verdict: {verdict}"


# ---------- 02-research.md 渲染 ----------


def render_research_md(slug: str, today: str, data: dict[str, Any]) -> str:
    cards_lines = []
    if not data["evidence_cards"]:
        cards_lines.append("_（无 evidence cards；纯 diagnosis-only 报告）_")
    for card in data["evidence_cards"]:
        cid = card["claim_id"]
        ctext = card["claim_text"].strip()
        status = card["status"]
        status_marker = {
            "covered": "✅ covered",
            "source_needed": "🔍 source_needed",
            "weak": "⚠️ weak",
        }.get(status, status)

        src_lines = []
        if not card["sources"]:
            src_lines.append("_（无来源；status 应为 source_needed 或 weak）_")
        for j, src in enumerate(card["sources"], 1):
            src_lines.append(
                f"#### Source {j}: {src['title']}\n"
                f"- **Type**: {src['type']}\n"
                f"- **Date**: {src.get('date', '_unknown_')}\n"
                f"- **URL**: {src['url']}\n"
                f"- **Quote**: > {src['quote']}\n"
                f"- **Confidence**: {src['confidence']}"
            )
        src_block = "\n\n".join(src_lines)

        cards_lines.append(
            f"### {cid} — {ctext}\n\n"
            f"**Status**: {status_marker}\n\n"
            f"{src_block}"
        )
    cards_block = "\n\n".join(cards_lines)

    diag_lines = []
    for d in data["claim_diagnosis"]:
        risk_marker = {"L": "🟢 L", "M": "🟡 M", "H": "🔴 H"}.get(d["risk"], d["risk"])
        counter = (d.get("counter_evidence") or "").strip() or "_（无）_"
        diag_lines.append(
            f"### {d['claim_id']} — {d['claim_text'].strip()}\n"
            f"- **Type**: {d['type']}\n"
            f"- **Evidence Required**: {d['evidence_required']}\n"
            f"- **Evidence Available**: {d['evidence_available']}\n"
            f"- **Counter-Evidence**: {counter}\n"
            f"- **Confidence**: {d['confidence']}\n"
            f"- **Risk**: {risk_marker}\n"
            f"- **Safer Rewrite**:\n  > {d['safer_rewrite']}"
        )
    diag_block = "\n\n".join(diag_lines)

    cred_marker = {
        "high": "🟢 high",
        "medium": "🟡 medium",
        "low": "🔴 low",
    }.get(data["overall_credibility"], data["overall_credibility"])

    high_risk = data["high_risk_claims"]
    high_risk_str = ", ".join(high_risk) if high_risk else "_（无）_"

    actions = data.get("recommended_actions") or []
    actions_block = (
        "\n".join(f"- {a}" for a in actions) if actions else "_（无；diagnosis 无遗留事项）_"
    )

    notes = (data.get("notes") or "").strip() or "_（无）_"
    user_decision = data.get("user_decision")
    user_decision_str = user_decision if user_decision else "_（不适用）_"

    bank_writes = data.get("evidence_bank_writes") or []
    if bank_writes:
        bank_lines = []
        for b in bank_writes:
            n = len(b["sources"])
            bank_lines.append(f"- `{b['topic']}` — {n} source(s) appended")
        bank_block = "\n".join(bank_lines)
    else:
        bank_block = "_（未沉淀到 evidence bank；如需跨文章复用，下次 commit 加 evidence_bank_writes）_"

    return f"""# 02-research — {slug}

> 由 `/szw-research` 在 {today} 产出。
> Brief reference: `01-brief.md`
> 内部循环：{data["loop_rounds"]} 轮 · 结论：`{data["verdict"]}`

## §1 Evidence Cards

{cards_block}

---

## §2 Claim Diagnosis

{diag_block}

---

## §3 Recommended Action

- **Overall Credibility**: {cred_marker}
- **High-Risk Claims**: {high_risk_str}
- **Loop Rounds**: {data["loop_rounds"]}
- **Verdict**: `{data["verdict"]}`
- **User Decision**: {user_decision_str}

### Action Items

{actions_block}

### Notes

{notes}

### Evidence Bank Sync

{bank_block}
"""


# ---------- evidence bank 同步 ----------


def append_to_evidence_bank(
    column_root: Path,
    topic: str,
    sources: list[dict[str, Any]],
    slug: str,
    today: str,
) -> tuple[bool, str]:
    """
    `.zero/evidence/<topic>.md` 不存在则创建（带 H1 + meta + ## Sources）；存在则在 ## Sources 末尾追加。
    返回 (created, path)。created=True 表示新建文件。
    """
    evidence_dir = column_root / EVIDENCE_DIR
    evidence_dir.mkdir(parents=True, exist_ok=True)
    file_path = evidence_dir / f"{topic}.md"

    new_blocks = []
    for src in sources:
        from_claim = src.get("from_claim", "?")
        new_blocks.append(
            f"### {src['title']} ({src.get('date', 'unknown')})\n"
            f"- **URL**: {src['url']}\n"
            f"- **Quote**: > {src['quote']}\n"
            f"- **Confidence**: {src['confidence']}\n"
            f"- **Used in**: `{slug}` (claim {from_claim}, added {today})"
        )
    addition = "\n\n".join(new_blocks)

    created = not file_path.exists()
    if created:
        content = f"""# Evidence: {topic}

> Auto-collected by `/szw-research`. Last updated: {today}

## Sources

{addition}
"""
        file_path.write_text(content, encoding="utf-8")
    else:
        old = file_path.read_text(encoding="utf-8")
        # 更新 Last updated 行
        old = re.sub(
            r"^>\s*Auto-collected.*Last updated:\s*\S+",
            f"> Auto-collected by `/szw-research`. Last updated: {today}",
            old,
            count=1,
            flags=re.MULTILINE,
        )
        # 追加到文件末
        if not old.endswith("\n"):
            old += "\n"
        old += "\n" + addition + "\n"
        file_path.write_text(old, encoding="utf-8")

    return created, str(file_path.relative_to(column_root))


# ---------- commit ----------


def cmd_commit(column_root: Path, slug: str) -> int:
    article_dir = column_root / ARTICLES_DIR / slug
    article_md = article_dir / "ARTICLE.md"
    brief_md = article_dir / "01-brief.md"
    if not article_md.exists():
        print(f"ERROR: ARTICLE.md not found: {article_md}", file=sys.stderr)
        return 2
    if not brief_md.exists():
        print(
            f"ERROR: 01-brief.md not found: {brief_md}\n"
            f"Run /szw-discuss {slug} first.",
            file=sys.stderr,
        )
        return 2

    state_path = column_root / STATE_REL_PATH
    if not state_path.exists():
        print(f"ERROR: STATE.md not found: {state_path}", file=sys.stderr)
        return 3

    raw = sys.stdin.read()
    if not raw.strip():
        print("ERROR: stdin is empty; expected research JSON", file=sys.stderr)
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

    allowed, msg = check_verdict_gate(data)
    if not allowed:
        print(f"ERROR: {msg}", file=sys.stderr)
        return 5

    today = date.today().isoformat()
    research_md = render_research_md(slug, today, data)
    research_path = article_dir / "02-research.md"
    research_path.write_text(research_md, encoding="utf-8")

    update_article_frontmatter(
        article_md,
        new_status="research_done",
        today=today,
        extra_log="research_done via /szw-research",
    )

    try:
        update_active_row(
            state_path,
            slug=slug,
            new_status="research_done",
            today=today,
            new_next_action="/szw-outline",
        )
    except ValueError as e:
        print(f"ERROR: STATE.md update failed: {e}", file=sys.stderr)
        return 3

    bank_writes = data.get("evidence_bank_writes") or []
    bank_log = []
    for b in bank_writes:
        created, rel = append_to_evidence_bank(
            column_root, b["topic"], b["sources"], slug, today
        )
        bank_log.append((rel, "created" if created else "appended", len(b["sources"])))

    print(f"✅ Committed research for {slug}")
    print(f"   wrote: {research_path.relative_to(column_root)}")
    print(f"   updated: {article_md.relative_to(column_root)} (status → research_done)")
    print(f"   updated: STATE.md (Active row → research_done)")
    if bank_log:
        for rel, action, n in bank_log:
            print(f"   evidence bank: {rel} ({action}, {n} source{'s' if n != 1 else ''})")
    if data["verdict"] == "passed_with_high_risk":
        hr = ", ".join(data["high_risk_claims"])
        print(f"   ⚠️  HIGH-risk accepted: {hr} (consider safer_rewrite at /szw-write)")
    print(f"\n👉 Next: /szw-outline {slug}")
    return 0


# ---------- main ----------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Finalize szw-research")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_commit = sub.add_parser("commit", help="Render research + advance status")
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
