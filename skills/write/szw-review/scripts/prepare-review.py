#!/usr/bin/env python3
"""
prepare-review.py — Phase 0：收集 szw-review 所需上下文

用法:
  ./prepare-review.py [--slug <slug>]

行为:
  - 无 --slug：取 STATE.md 优先级路由：draft_done > review_failed > review_passed > 其他 active
  - 验证 04-draft.md 必需存在
  - 列 brief / outline / research / EDITORIAL_CONTEXT / ADR / glossary 路径供 AI 按需 Read
  - 读 szw-config.json 拿 style_capture 配置（enabled / diff_threshold_pct / merge_after_n_reviews / min_pattern_frequency）
  - 找最近一份 writing-history snapshot（非 INDEX.md）→ 计算与 04-draft.md 的 diff 比例 → 推荐 phase2 是否跳过
  - 列 .zero/style-profile.md 路径（已有则给 AI；不存在 phase2 首次执行将创建）

退出码:
  0  成功
  1  不在专栏目录
  2  slug / ARTICLE.md / 04-draft.md 不存在
  3  STATE.md 缺失 / 默认路由失败
  4  ARTICLE.md frontmatter 解析失败
  5  szw-config.json 解析失败

设计原则:
  - 只读，不修改任何文件
  - diff 用 difflib.SequenceMatcher（行级），返回 1 - similarity 作为变更比例
  - 找不到 history snapshot 时 phase2_should_skip=true（理由：no baseline）
"""

from __future__ import annotations

import argparse
import difflib
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
ADR_FILENAME_RE = re.compile(r"^(\d{4})-(.+)\.md$")
ADR_TITLE_RE = re.compile(r"^#\s+(.+)$")
SNAPSHOT_NN_RE = re.compile(r"^(\d+)-")

STATUS_PRIORITY = ["draft_done", "review_failed", "review_passed"]

DEFAULT_STYLE_CAPTURE = {
    "enabled": True,
    "diff_threshold_pct": 5,
    "merge_after_n_reviews": 10,
    "min_pattern_frequency": 3,
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
        f"szw-config.json not found in {start} or any parent directory.\n"
        "Run /szw-init first to initialize a column."
    )


# ---------- STATE.md ----------


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
    for status in STATUS_PRIORITY:
        bucket = [r for r in rows if r.get("Status", "").strip() == status]
        valid = [r for r in bucket if DATE_RE.match(r.get("Last touched", ""))]
        if valid:
            valid.sort(key=lambda r: r["Last touched"], reverse=True)
            return valid[0].get("Slug", "").strip() or None
    valid = [r for r in rows if DATE_RE.match(r.get("Last touched", ""))]
    if not valid:
        return None
    valid.sort(key=lambda r: r["Last touched"], reverse=True)
    return valid[0].get("Slug", "").strip() or None


# ---------- ARTICLE.md ----------


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


# ---------- config 读取 ----------


def load_style_capture_config(column_root: Path) -> dict[str, Any]:
    cfg_path = column_root / CONFIG_REL_PATH
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"szw-config.json parse failed: {e}")
    sc = dict(DEFAULT_STYLE_CAPTURE)
    raw = data.get("style_capture") or {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            if k in sc:
                sc[k] = v
    return sc


# ---------- writing-history 找最近 snapshot ----------


def find_latest_snapshot(slug_history_dir: Path) -> Path | None:
    if not slug_history_dir.exists():
        return None
    latest = None
    latest_nn = -1
    for f in slug_history_dir.iterdir():
        if not f.is_file() or f.name == "INDEX.md":
            continue
        m = SNAPSHOT_NN_RE.match(f.name)
        if m:
            nn = int(m.group(1))
            if nn > latest_nn:
                latest_nn = nn
                latest = f
    return latest


def strip_snapshot_header(content: str) -> str:
    """剥离 snapshot 文件开头的 <!-- meta --> 块"""
    m = re.match(r"<!--\s*\n.*?-->\s*\n+", content, re.DOTALL)
    if m:
        return content[m.end() :]
    return content


def compute_diff_pct(current: str, snapshot_body: str) -> float:
    """返回 1 - SequenceMatcher.ratio() 作为变更比例（0.0-1.0）"""
    sm = difflib.SequenceMatcher(None, snapshot_body, current)
    return round(1.0 - sm.ratio(), 4)


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
            {"id": m.group(1), "title": title or f.stem, "path": str(f.relative_to(column_root))}
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


# ---------- main ----------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Prepare szw-review context")
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
                "Run /szw-write first to produce a draft.",
                file=sys.stderr,
            )
            return 3

    article_dir = column_root / ARTICLES_DIR / slug
    article_md = article_dir / "ARTICLE.md"
    draft_md = article_dir / "04-draft.md"
    brief_md = article_dir / "01-brief.md"
    outline_md = article_dir / "03-outline.md"
    research_md = article_dir / "02-research.md"

    if not article_md.exists():
        print(f"ERROR: ARTICLE.md not found: {article_md.relative_to(column_root)}", file=sys.stderr)
        return 2
    if not draft_md.exists():
        print(
            f"ERROR: 04-draft.md not found: {draft_md.relative_to(column_root)}\n"
            f"Run /szw-write {slug} first.",
            file=sys.stderr,
        )
        return 2

    raw = article_md.read_text(encoding="utf-8")
    try:
        fm, _ = parse_frontmatter(raw)
    except ValueError as e:
        print(f"ERROR: ARTICLE.md frontmatter parse failed: {e}", file=sys.stderr)
        return 4

    try:
        style_cfg = load_style_capture_config(column_root)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 5

    # writing history 与 diff
    slug_hist_dir = column_root / WRITING_HISTORY_DIR / slug
    latest_snapshot = find_latest_snapshot(slug_hist_dir)
    diff_pct = None
    snapshot_meta = None
    phase2_skip_reason = None

    if not style_cfg["enabled"]:
        phase2_skip_reason = "style_capture.enabled=false in szw-config.json"
    elif latest_snapshot is None:
        phase2_skip_reason = "no writing-history snapshot found (first review or history wiped)"
    else:
        snap_text = latest_snapshot.read_text(encoding="utf-8")
        snap_body = strip_snapshot_header(snap_text)
        current = draft_md.read_text(encoding="utf-8")
        diff_pct = compute_diff_pct(current, snap_body) * 100  # to %
        threshold = style_cfg["diff_threshold_pct"]
        snapshot_meta = {
            "filename": latest_snapshot.name,
            "modified": datetime.fromtimestamp(
                latest_snapshot.stat().st_mtime
            ).date().isoformat(),
            "size_bytes": latest_snapshot.stat().st_size,
        }
        if diff_pct < threshold:
            phase2_skip_reason = (
                f"diff_pct={diff_pct:.2f}% < threshold={threshold}% "
                f"(no significant author edits since last AI snapshot)"
            )

    style_profile_path = column_root / STYLE_PROFILE_REL
    editorial_context = column_root / EDITORIAL_CONTEXT_NAME
    adrs = list_adrs(column_root)
    glossary = list_glossary(column_root)

    current_status = fm.get("status")
    warnings = []
    if current_status not in {"draft_done", "review_failed", "review_passed"}:
        warnings.append(
            f"status='{current_status}' (not draft/review state); "
            "review still allowed but unusual"
        )
    if current_status == "review_passed":
        warnings.append(
            "status='review_passed' already; re-running review will overwrite 05-review.md"
        )
    if not research_md.exists():
        warnings.append(
            "02-research.md missing; Phase 1 边界审 / 反方审无法对照 evidence cards"
        )
    if not outline_md.exists():
        warnings.append(
            "03-outline.md missing; Phase 1 acceptance_criteria 检查跳过"
        )
    if not style_profile_path.exists() and style_cfg["enabled"]:
        warnings.append(
            "style-profile.md 不存在；Phase 2 首次执行将创建（如未跳过）"
        )

    payload = {
        "column_root": str(column_root),
        "slug": slug,
        "article_md_path": str(article_md.relative_to(column_root)),
        "draft_md_path": str(draft_md.relative_to(column_root)),
        "brief_md_path": str(brief_md.relative_to(column_root)) if brief_md.exists() else None,
        "outline_md_path": str(outline_md.relative_to(column_root)) if outline_md.exists() else None,
        "research_md_path": str(research_md.relative_to(column_root)) if research_md.exists() else None,
        "current_status": current_status,
        "type": fm.get("type"),
        "title": fm.get("title"),
        "target_platforms": fm.get("target_platforms"),
        "long_term_assets": {
            "editorial_context": (
                str(editorial_context.relative_to(column_root))
                if editorial_context.exists()
                else None
            ),
            "style_profile": (
                str(style_profile_path.relative_to(column_root))
                if style_profile_path.exists()
                else None
            ),
            "adrs": adrs,
            "glossary": glossary,
        },
        "phase2_context": {
            "config": style_cfg,
            "latest_snapshot": snapshot_meta,
            "diff_pct": diff_pct,
            "should_skip": phase2_skip_reason is not None,
            "skip_reason": phase2_skip_reason,
        },
        "warnings": warnings,
    }

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
