#!/usr/bin/env python3
"""
finalize-review.py — Phase 3：把反审 + 风格捕获结果落盘 + 推进状态

子命令:
  commit --slug <slug>     # 从 stdin 读 JSON，渲染 05-review.md，更新 ARTICLE.md / STATE.md，
                            # 可选追加到 .zero/style-profile.md（Phase 2 未跳过时）

stdin JSON schema（参考 references/review-schema.md）:
  {
    "phase1": {
      "loop_rounds": 0,
      "issues": [
        {
          "id": "I1",
          "severity": "HIGH" | "MEDIUM" | "LOW",
          "category": "fact|counterargument|boundary|style|claim",
          "location": "S2 / §3 paragraph 2 / overall",
          "description": "...",
          "evidence": "...",
          "suggestion": "..."
        }
      ],
      "summary": "..."
    },
    "phase2": {
      "skipped": true,                        // 若 true，下面字段可缺
      "skip_reason": "diff < threshold",
      "diff_pct": 12.5,                        // 仅 not skipped 时有
      "snapshot_compared": "01-both-full-...md",
      "features": {                           // 仅 not skipped 时有
        "vocabulary_substitutions": [
          {"ai_pref": "...", "author_pref": "...", "frequency": 3, "examples": ["..."]}
        ],
        "sentence_patterns": [
          {"pattern": "...", "frequency": 2, "examples": ["..."]}
        ],
        "rhythm_paragraph": ["short sentences preferred"],
        "punctuation_mixing": ["—— preferred over --"],
        "anti_patterns": ["..."]
      }
    },
    "verdict": "review_passed" | "review_failed",
    "notes": "..."
  }

退出码:
  0  成功
  1  不在专栏目录
  2  slug / ARTICLE.md / 04-draft.md 不存在
  3  STATE.md 缺失 / 解析失败
  4  stdin JSON 缺字段 / 字段值非法
  5  verdict gate：HIGH issues 存在但 verdict=review_passed（自相矛盾）
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
STYLE_PROFILE_REL = ".zero/style-profile.md"

PLACEHOLDER_RE = re.compile(r"^<.*>$")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|$")
HEADING_RE = re.compile(r"^##\s+(.+)$")

VALID_SEVERITY = {"HIGH", "MEDIUM", "LOW"}
VALID_CATEGORY = {"fact", "counterargument", "boundary", "style", "claim"}
VALID_VERDICT = {"review_passed", "review_failed"}

REQUIRED_TOP_FIELDS = {"phase1", "phase2", "verdict"}
REQUIRED_PHASE1_FIELDS = {"loop_rounds", "issues"}
REQUIRED_ISSUE_FIELDS = {"id", "severity", "category", "location", "description", "suggestion"}


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


# ---------- ARTICLE.md / STATE.md 改写（沿用既有模式） ----------


def get_article_status(article_md_path: Path) -> str | None:
    content = article_md_path.read_text(encoding="utf-8")
    m = re.search(r"^status:\s*(\S+)\s*$", content, re.MULTILINE)
    return m.group(1) if m else None


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
    if data["verdict"] not in VALID_VERDICT:
        return False, f"verdict must be one of {sorted(VALID_VERDICT)}"

    p1 = data["phase1"]
    if not isinstance(p1, dict):
        return False, "phase1 must be object"
    miss = REQUIRED_PHASE1_FIELDS - set(p1.keys())
    if miss:
        return False, f"phase1 missing fields: {sorted(miss)}"
    if not isinstance(p1["loop_rounds"], int) or p1["loop_rounds"] < 0:
        return False, "phase1.loop_rounds must be non-negative int"
    if not isinstance(p1["issues"], list):
        return False, "phase1.issues must be list"
    for i, iss in enumerate(p1["issues"]):
        if not isinstance(iss, dict):
            return False, f"phase1.issues[{i}] must be object"
        miss = REQUIRED_ISSUE_FIELDS - set(iss.keys())
        if miss:
            return False, f"phase1.issues[{i}] missing fields: {sorted(miss)}"
        if iss["severity"] not in VALID_SEVERITY:
            return False, (
                f"phase1.issues[{i}].severity must be one of {sorted(VALID_SEVERITY)}"
            )
        if iss["category"] not in VALID_CATEGORY:
            return False, (
                f"phase1.issues[{i}].category must be one of {sorted(VALID_CATEGORY)}"
            )

    p2 = data["phase2"]
    if not isinstance(p2, dict):
        return False, "phase2 must be object"
    if "skipped" not in p2:
        return False, "phase2.skipped is required (true/false)"
    if not isinstance(p2["skipped"], bool):
        return False, "phase2.skipped must be bool"
    if not p2["skipped"]:
        if "features" not in p2:
            return False, "phase2.features required when not skipped"
        feats = p2["features"]
        if not isinstance(feats, dict):
            return False, "phase2.features must be object"
        # 至少有一个特征类别非空（避免 phase2 跑了但什么都没学到）
        feat_keys = [
            "vocabulary_substitutions",
            "sentence_patterns",
            "rhythm_paragraph",
            "punctuation_mixing",
            "anti_patterns",
        ]
        for k in feat_keys:
            if k in feats and not isinstance(feats[k], list):
                return False, f"phase2.features.{k} must be list"

    return True, ""


def check_verdict_gate(data: dict[str, Any]) -> tuple[bool, str]:
    """HIGH issue 存在但 verdict=review_passed → 拒绝"""
    high_count = sum(
        1 for iss in data["phase1"]["issues"] if iss["severity"] == "HIGH"
    )
    if high_count >= 1 and data["verdict"] == "review_passed":
        ids = [iss["id"] for iss in data["phase1"]["issues"] if iss["severity"] == "HIGH"]
        return False, (
            f"verdict='review_passed' but {high_count} HIGH issue(s) present: {ids}. "
            "Self-contradictory. Set verdict='review_failed' (and address via /szw-write polish), "
            "or downgrade those issues to MEDIUM/LOW with justification."
        )
    return True, ""


# ---------- 05-review.md 渲染 ----------


def render_review_md(slug: str, today: str, data: dict[str, Any]) -> str:
    p1 = data["phase1"]
    issues = p1["issues"]

    # 统计
    high = [i for i in issues if i["severity"] == "HIGH"]
    medium = [i for i in issues if i["severity"] == "MEDIUM"]
    low = [i for i in issues if i["severity"] == "LOW"]

    severity_marker = {"HIGH": "🔴 HIGH", "MEDIUM": "🟡 MEDIUM", "LOW": "🟢 LOW"}

    def render_issues(group: list[dict], group_name: str) -> str:
        if not group:
            return f"_（无 {group_name} issue）_"
        lines = []
        for iss in group:
            evidence = (iss.get("evidence") or "").strip() or "_（无）_"
            lines.append(
                f"#### {iss['id']} · {severity_marker[iss['severity']]} · "
                f"`{iss['category']}` · `{iss['location']}`\n\n"
                f"**Description**: {iss['description']}\n\n"
                f"**Evidence**: {evidence}\n\n"
                f"**Suggestion**: {iss['suggestion']}"
            )
        return "\n\n".join(lines)

    high_block = render_issues(high, "HIGH")
    medium_block = render_issues(medium, "MEDIUM")
    low_block = render_issues(low, "LOW")

    summary = (p1.get("summary") or "").strip() or "_（未提供整体说明）_"

    p2 = data["phase2"]
    if p2["skipped"]:
        skip_reason = (p2.get("skip_reason") or "").strip() or "未给理由"
        phase2_block = f"⏭ Phase 2 跳过\n\n**原因**：{skip_reason}"
    else:
        diff_pct = p2.get("diff_pct", "?")
        snap = p2.get("snapshot_compared", "?")
        feats = p2.get("features", {})

        def render_feat_table(items: list[dict[str, Any]], cols: list[str]) -> str:
            if not items:
                return "_（无）_"
            header = "| " + " | ".join(cols) + " |"
            sep = "|" + "|".join("---" for _ in cols) + "|"
            rows = []
            for it in items:
                vals = []
                for c in cols:
                    v = it.get(c, "")
                    if isinstance(v, list):
                        v = "; ".join(v)
                    vals.append(str(v))
                rows.append("| " + " | ".join(vals) + " |")
            return "\n".join([header, sep] + rows)

        vocab_block = render_feat_table(
            feats.get("vocabulary_substitutions", []),
            ["ai_pref", "author_pref", "frequency"],
        )
        sentence_block = render_feat_table(
            feats.get("sentence_patterns", []), ["pattern", "frequency"]
        )
        rhythm = feats.get("rhythm_paragraph", []) or []
        punct = feats.get("punctuation_mixing", []) or []
        anti = feats.get("anti_patterns", []) or []
        rhythm_block = "\n".join(f"- {r}" for r in rhythm) if rhythm else "_（无）_"
        punct_block = "\n".join(f"- {p}" for p in punct) if punct else "_（无）_"
        anti_block = "\n".join(f"- {a}" for a in anti) if anti else "_（无）_"

        phase2_block = f"""✅ Phase 2 已执行

- **Snapshot 对比**：`{snap}`
- **Diff %**：{diff_pct}%

#### Vocabulary Substitutions
{vocab_block}

#### Sentence Patterns
{sentence_block}

#### Rhythm / Paragraph
{rhythm_block}

#### Punctuation / Mixing
{punct_block}

#### Anti-Patterns
{anti_block}"""

    notes = (data.get("notes") or "").strip() or "_（无）_"
    verdict_marker = (
        "✅ review_passed" if data["verdict"] == "review_passed" else "❌ review_failed"
    )

    return f"""# 05-review — {slug}

> 由 `/szw-review` 在 {today} 产出。
> 内部循环：{p1["loop_rounds"]} 轮 · 结论：{verdict_marker}

## §1 Phase 1 — Skeptical Review

**统计**：HIGH={len(high)}, MEDIUM={len(medium)}, LOW={len(low)}

**整体说明**：{summary}

### HIGH issues

{high_block}

### MEDIUM issues

{medium_block}

### LOW issues

{low_block}

---

## §2 Phase 2 — Style Capture

{phase2_block}

---

## §3 Notes

{notes}
"""


# ---------- style-profile.md 累积 ----------


def append_to_style_profile(
    column_root: Path,
    slug: str,
    today: str,
    features: dict[str, Any],
) -> tuple[bool, int]:
    """
    把 features 5 类追加到 .zero/style-profile.md 的 ## Recent Edits 表。
    文件不存在则创建。
    返回 (created, n_edits_added)
    """
    sp_path = column_root / STYLE_PROFILE_REL
    sp_path.parent.mkdir(parents=True, exist_ok=True)

    # 把 features 转成行：每条规则一行
    new_rows: list[str] = []
    for sub in features.get("vocabulary_substitutions", []) or []:
        ai = sub.get("ai_pref", "")
        au = sub.get("author_pref", "")
        freq = sub.get("frequency", 1)
        new_rows.append(
            f"| {today} | {slug} | vocab | AI 用 `{ai}` → 作者 `{au}` (freq={freq}) |"
        )
    for sp in features.get("sentence_patterns", []) or []:
        pat = sp.get("pattern", "")
        freq = sp.get("frequency", 1)
        new_rows.append(
            f"| {today} | {slug} | sentence | 偏好 `{pat}` (freq={freq}) |"
        )
    for r in features.get("rhythm_paragraph", []) or []:
        new_rows.append(f"| {today} | {slug} | rhythm | {r} |")
    for p in features.get("punctuation_mixing", []) or []:
        new_rows.append(f"| {today} | {slug} | punctuation | {p} |")
    for a in features.get("anti_patterns", []) or []:
        new_rows.append(f"| {today} | {slug} | anti-pattern | 删除 `{a}` |")

    if not new_rows:
        # phase2 跑了但 features 全空 → 不写
        return False, 0

    new_block = "\n".join(new_rows)
    n_added = len(new_rows)

    if not sp_path.exists():
        # 首次创建
        article_word = "article"  # first time, always 1
        edit_word = "edit instance" if n_added == 1 else "edit instances"
        content = f"""# Author Style Profile

> Auto-generated by `/szw-review` Phase 2; consumed by `/szw-write` Phase 1+2.
> Last updated: {today}; sample size: 1 {article_word}, {n_added} {edit_word}.

## Stable Patterns（频次 ≥ 3，已合并）

### Vocabulary Substitutions
| AI 倾向 | 作者偏好 | 频次 | 来源 |
|---|---|---|---|

### Sentence / Rhythm

_(待累积)_

### Anti-Patterns（用户反复删除）

_(待累积)_

## Recent Edits（待合并的增量，每次 review 追加）

| 日期 | Article | Category | Detail |
|---|---|---|---|
{new_block}
"""
        sp_path.write_text(content, encoding="utf-8")
        return True, n_added

    # 已存在 → 追加
    old = sp_path.read_text(encoding="utf-8")

    # 1) 更新 meta blockquote 的 Last updated + 累计计数
    meta_re = re.compile(
        r"(>\s*Last updated:\s*)\S+(;\s*sample size:\s*)(\d+)\s+articles?,\s*(\d+)\s+edit instances?\.",
        re.MULTILINE,
    )
    m = meta_re.search(old)
    if m:
        old_articles = int(m.group(3))
        old_edits = int(m.group(4))
        # 文章数 +1（每次 commit 算 1 篇贡献；同 slug 多次 review 累计统计；后续 audit 可去重）
        new_articles = old_articles + 1
        new_edits = old_edits + n_added
        article_word = "article" if new_articles == 1 else "articles"
        edit_word = "edit instance" if new_edits == 1 else "edit instances"
        old = meta_re.sub(
            f"\\g<1>{today}\\g<2>{new_articles} {article_word}, {new_edits} {edit_word}.",
            old,
            count=1,
        )

    # 2) 在 ## Recent Edits 表末尾追加新行
    # 找 Recent Edits H2，再找其下第一个表的末尾
    recent_pattern = re.compile(
        r"^(##[ \t]+Recent Edits[^\n]*\n.*?\|[ \t]*日期[ \t]*\|.*?\n\|[\s\-:|]+\|\n)(.*?)(?=^##[ \t]|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m2 = recent_pattern.search(old)
    if m2:
        existing_rows = m2.group(2).rstrip("\n")
        replacement = (
            m2.group(1)
            + (existing_rows + "\n" if existing_rows else "")
            + new_block
            + "\n\n"
        )
        old = old[: m2.start()] + replacement + old[m2.end() :]
    else:
        # 兜底：表损坏，文件末追加
        if not old.endswith("\n"):
            old += "\n"
        old += "\n## Recent Edits\n\n| 日期 | Article | Category | Detail |\n|---|---|---|---|\n" + new_block + "\n"

    sp_path.write_text(old, encoding="utf-8")
    return False, n_added


# ---------- next action 决策 ----------


def derive_next_action(verdict: str, issues: list[dict[str, Any]], slug: str) -> str:
    """生成完整的下一步命令字串（含 slug）。"""
    if verdict == "review_passed":
        return f"/szw-publish {slug}"
    # review_failed: 找第一个 HIGH 的 location
    high = [i for i in issues if i["severity"] == "HIGH"]
    if not high:
        # review_failed 但无 HIGH（用户基于 MEDIUM 决定 fail）
        return f"/szw-write {slug} --mode polish"
    loc = high[0].get("location", "")
    # 试着提取 S<n>
    m = re.search(r"\bS(\d+)\b", loc)
    if m:
        return f"/szw-write {slug} S{m.group(1)} --mode polish"
    return f"/szw-write {slug} --mode polish"


# ---------- commit ----------


def cmd_commit(column_root: Path, slug: str) -> int:
    article_dir = column_root / ARTICLES_DIR / slug
    article_md = article_dir / "ARTICLE.md"
    draft_md = article_dir / "04-draft.md"
    if not article_md.exists():
        print(f"ERROR: ARTICLE.md not found: {article_md}", file=sys.stderr)
        return 2
    if not draft_md.exists():
        print(f"ERROR: 04-draft.md not found: {draft_md}", file=sys.stderr)
        return 2

    state_path = column_root / STATE_REL_PATH
    if not state_path.exists():
        print(f"ERROR: STATE.md not found: {state_path}", file=sys.stderr)
        return 3

    raw = sys.stdin.read()
    if not raw.strip():
        print("ERROR: stdin is empty; expected review JSON", file=sys.stderr)
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
    review_md = render_review_md(slug, today, data)
    review_path = article_dir / "05-review.md"
    review_path.write_text(review_md, encoding="utf-8")

    # ARTICLE.md
    new_status = data["verdict"]
    update_article_frontmatter(
        article_md,
        new_status=new_status,
        today=today,
        extra_log=f"{new_status} via /szw-review (loops={data['phase1']['loop_rounds']})",
    )

    # STATE.md
    next_action = derive_next_action(new_status, data["phase1"]["issues"], slug)
    try:
        update_active_row(
            state_path,
            slug=slug,
            new_status=new_status,
            today=today,
            new_next_action=next_action,
        )
    except ValueError as e:
        print(f"ERROR: STATE.md update failed: {e}", file=sys.stderr)
        return 3

    # style-profile
    style_log = None
    p2 = data["phase2"]
    if not p2["skipped"]:
        feats = p2.get("features", {})
        created, n_added = append_to_style_profile(
            column_root,
            slug=slug,
            today=today,
            features=feats,
        )
        if n_added > 0:
            style_log = (
                f".zero/style-profile.md "
                f"({'created' if created else 'appended'}, {n_added} edit row(s))"
            )

    # 输出
    issues = data["phase1"]["issues"]
    high = sum(1 for i in issues if i["severity"] == "HIGH")
    medium = sum(1 for i in issues if i["severity"] == "MEDIUM")
    low = sum(1 for i in issues if i["severity"] == "LOW")
    print(f"✅ Committed review for {slug}")
    print(f"   verdict: {new_status}")
    print(f"   wrote: {review_path.relative_to(column_root)}")
    print(f"   issues: HIGH={high}, MEDIUM={medium}, LOW={low}")
    print(f"   updated: {article_md.relative_to(column_root)} (status → {new_status})")
    print(f"   updated: STATE.md (next: {next_action})")
    if style_log:
        print(f"   {style_log}")
    elif p2["skipped"]:
        print(f"   Phase 2 skipped: {p2.get('skip_reason', '?')}")
    print(f"\n👉 Next: {next_action}")
    return 0


# ---------- main ----------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Finalize szw-review")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_commit = sub.add_parser("commit", help="Render review + advance status + accumulate style-profile")
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
