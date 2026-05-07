#!/usr/bin/env python3
"""
new-article.py — 创建新 article 项目（写 ARTICLE.md + 更新 STATE.md）

用法:
  ./new-article.py --slug <slug> --type <type> [--platforms <p1,p2>] \\
                   [--title <title>] [--from-inbox <slug>] [--series <name>]

参数:
  --slug         必需。`YYYY-MM-<topic>` 格式，小写字母数字 + 连字符
  --type         必需。industry-analysis / programmer-advice / product-analysis / tech-blog
  --platforms    可选。逗号分隔（默认从 .zero/szw-config.json 读 default_platforms）
  --title        可选。working title；默认从 slug 推（去掉日期前缀，连字符 → 空格）
  --from-inbox   可选。从 inbox/pending/<slug>.md 读内容预填，移到 inbox/done/
  --series       可选。系列名；要求 series/<name>/INDEX.md 已存在

退出码:
  0   成功
  1   不在专栏目录（找不到 .zero/szw-config.json）
  2   slug 冲突（articles/<slug>/ 已存在）
  3   slug 格式非法
  4   article type 非法
  5   platform 非法
  6   --from-inbox 指定的文件不存在
  7   --series 指定的 INDEX.md 不存在
  8   STATE.md 缺失或解析失败

设计原则:
  - 非交互；所有决策由 AI 在调用前完成（参考 SKILL.md）
  - 原子性：任何一步失败，已创建的文件回滚（除 inbox 移动外）
  - 写 STATE.md 时保留所有未识别字段（仅在 ## Active Articles 表内插入新行）
  - 占位行（含 <...> 形式单元格）自动清理
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

CONFIG_REL_PATH = ".zero/szw-config.json"
STATE_REL_PATH = ".zero/STATE.md"

ARTICLE_TYPES = {
    "industry-analysis",
    "programmer-advice",
    "product-analysis",
    "tech-blog",
}

VALID_PLATFORMS = {"blog", "wechat", "x", "xhs"}

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PLACEHOLDER_RE = re.compile(r"^<.*>$")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|$")
HEADING_RE = re.compile(r"^##\s+(.+)$")

TEMPLATE_NAME = "ARTICLE.md"


# ---------- column root 定位 ----------


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


# ---------- 验证 ----------


def validate_slug(slug: str) -> None:
    if not SLUG_RE.match(slug):
        raise ValueError(
            f"slug '{slug}' must be lowercase alphanumeric + hyphens, "
            "starting with alphanumeric (e.g. 2026-05-skills-vs-gsd)"
        )


def validate_type(article_type: str) -> None:
    if article_type not in ARTICLE_TYPES:
        raise ValueError(
            f"type '{article_type}' invalid; must be one of {sorted(ARTICLE_TYPES)}"
        )


def validate_platforms(platforms: list[str]) -> None:
    bad = [p for p in platforms if p not in VALID_PLATFORMS]
    if bad:
        raise ValueError(
            f"platforms {bad} invalid; valid items: {sorted(VALID_PLATFORMS)}"
        )


# ---------- 默认值 ----------


def default_platforms_from_config(column_root: Path) -> list[str]:
    config_path = column_root / CONFIG_REL_PATH
    with config_path.open() as f:
        data = json.load(f)
    platforms = data.get("default_platforms", ["blog", "wechat"])
    if not isinstance(platforms, list):
        raise ValueError(f"default_platforms in config is not a list: {platforms!r}")
    return platforms


def default_title_from_slug(slug: str) -> str:
    """2026-05-skills-vs-gsd → Skills vs GSD"""
    parts = slug.split("-")
    # 跳过开头 YYYY-MM 前缀
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        parts = parts[2:]
    if not parts:
        return slug
    return " ".join(p.capitalize() for p in parts)


# ---------- 模板渲染 ----------


def render_article_md(
    template_path: Path,
    slug: str,
    title: str,
    article_type: str,
    platforms: list[str],
    created_at: str,
    linked_series: str | None,
    linked_inbox: str | None,
    source_material: str,
) -> str:
    template = template_path.read_text(encoding="utf-8")
    substitutions = {
        "<SLUG>": slug,
        "<TITLE>": title,
        "<TYPE>": article_type,
        "<PLATFORMS>": ", ".join(platforms),
        "<CREATED_AT>": created_at,
        "<LINKED_SERIES>": linked_series if linked_series else "null",
        "<LINKED_INBOX>": linked_inbox if linked_inbox else "null",
        "<SOURCE_MATERIAL>": source_material,
    }
    out = template
    for key, val in substitutions.items():
        out = out.replace(key, val)
    return out


# ---------- STATE.md 写入 ----------


def append_to_active_table(state_md_path: Path, slug: str, today: str) -> None:
    """
    在 ## Active Articles 表的数据区顶部插入一行。
    清理占位行（任意单元格含 <...>）。
    """
    content = state_md_path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=False)

    new_row = f"| {slug} | created | {today} | /szw-discuss |"

    # 找 ## Active Articles 段
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
        raise ValueError("'## Active Articles' heading not found in STATE.md")
    if section_end is None:
        section_end = len(lines)

    # 在 section 内找表头 + 分隔行
    header_idx = None
    sep_idx = None
    for i in range(section_start + 1, section_end):
        if header_idx is None and TABLE_ROW_RE.match(lines[i]) and not TABLE_SEP_RE.match(lines[i]):
            header_idx = i
            continue
        if header_idx is not None and TABLE_SEP_RE.match(lines[i]):
            sep_idx = i
            break
    if header_idx is None or sep_idx is None:
        raise ValueError("Active Articles 表缺少表头或分隔行")

    # 数据区：sep_idx + 1 起，到下一非表行为止
    data_start = sep_idx + 1
    data_end = data_start
    while data_end < section_end and TABLE_ROW_RE.match(lines[data_end]):
        data_end += 1

    # 过滤占位行
    kept_data = []
    for line in lines[data_start:data_end]:
        m_row = TABLE_ROW_RE.match(line)
        if not m_row:
            kept_data.append(line)
            continue
        cells = [c.strip() for c in m_row.group(1).split("|")]
        if any(PLACEHOLDER_RE.match(c) for c in cells):
            continue  # 占位行删除
        kept_data.append(line)

    # 新行插在数据区最前
    new_data = [new_row] + kept_data

    new_lines = lines[: sep_idx + 1] + new_data + lines[data_end:]
    new_content = "\n".join(new_lines)
    if content.endswith("\n"):
        new_content += "\n"
    state_md_path.write_text(new_content, encoding="utf-8")


# ---------- inbox / series 关联 ----------


def consume_inbox(column_root: Path, inbox_slug: str) -> str:
    """
    读 inbox/pending/<slug>.md → 返回内容；移动到 inbox/done/。
    """
    pending = column_root / "inbox" / "pending" / f"{inbox_slug}.md"
    done_dir = column_root / "inbox" / "done"
    done_dir.mkdir(parents=True, exist_ok=True)
    done_path = done_dir / f"{inbox_slug}.md"

    content = pending.read_text(encoding="utf-8")
    shutil.move(str(pending), str(done_path))
    return f"<!-- imported from inbox/done/{inbox_slug}.md -->\n\n{content}"


def append_to_series_index(column_root: Path, series_name: str, slug: str, title: str, today: str) -> None:
    index_path = column_root / "series" / series_name / "INDEX.md"
    line = f"\n- [ ] {today} — `{slug}` — {title}\n"
    with index_path.open("a", encoding="utf-8") as f:
        f.write(line)


# ---------- main ----------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Create a new szw article project")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--type", required=True, dest="article_type")
    parser.add_argument("--platforms", default=None, help="Comma-separated; defaults from szw-config.json")
    parser.add_argument("--title", default=None)
    parser.add_argument("--from-inbox", default=None, dest="from_inbox")
    parser.add_argument("--series", default=None)
    args = parser.parse_args(argv[1:])

    # column root
    try:
        column_root = find_column_root(Path.cwd())
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    # slug 校验
    try:
        validate_slug(args.slug)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3

    # type 校验
    try:
        validate_type(args.article_type)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 4

    # 冲突检查
    article_dir = column_root / "articles" / args.slug
    if article_dir.exists():
        print(
            f"ERROR: articles/{args.slug}/ already exists. "
            "Pick a different slug or /szw-resume to continue.",
            file=sys.stderr,
        )
        return 2

    # platforms
    if args.platforms is not None:
        platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]
    else:
        try:
            platforms = default_platforms_from_config(column_root)
        except (ValueError, json.JSONDecodeError) as e:
            print(f"ERROR: failed to read default_platforms: {e}", file=sys.stderr)
            return 1
    try:
        validate_platforms(platforms)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 5

    # inbox 预检
    inbox_pending = None
    if args.from_inbox:
        inbox_pending = column_root / "inbox" / "pending" / f"{args.from_inbox}.md"
        if not inbox_pending.exists():
            print(
                f"ERROR: inbox file not found: {inbox_pending.relative_to(column_root)}",
                file=sys.stderr,
            )
            return 6

    # series 预检
    if args.series:
        series_index = column_root / "series" / args.series / "INDEX.md"
        if not series_index.exists():
            print(
                f"ERROR: series INDEX.md not found: {series_index.relative_to(column_root)}\n"
                "Run /szw-new-series (v2.0) first or create INDEX.md manually.",
                file=sys.stderr,
            )
            return 7

    # STATE.md 预检
    state_path = column_root / STATE_REL_PATH
    if not state_path.exists():
        print(f"ERROR: STATE.md not found at {state_path}", file=sys.stderr)
        return 8

    # title 默认值
    title = args.title if args.title else default_title_from_slug(args.slug)

    # source material
    if inbox_pending:
        source_material = consume_inbox(column_root, args.from_inbox)
    else:
        source_material = "> 起稿前的散乱材料 / 链接 / 引用粘贴在这里。"

    # 渲染 ARTICLE.md
    today = date.today().isoformat()
    template_path = (
        Path(__file__).resolve().parent.parent / "templates" / TEMPLATE_NAME
    )
    article_md = render_article_md(
        template_path=template_path,
        slug=args.slug,
        title=title,
        article_type=args.article_type,
        platforms=platforms,
        created_at=today,
        linked_series=args.series,
        linked_inbox=args.from_inbox,
        source_material=source_material,
    )

    # 落盘（先创建目录，再写文件）
    article_dir.mkdir(parents=True, exist_ok=False)
    article_md_path = article_dir / "ARTICLE.md"
    article_md_path.write_text(article_md, encoding="utf-8")

    # 更新 STATE.md
    try:
        append_to_active_table(state_path, args.slug, today)
    except ValueError as e:
        # 回滚：删除已创建的 article 目录
        shutil.rmtree(article_dir)
        print(f"ERROR: STATE.md update failed: {e}", file=sys.stderr)
        return 8

    # 更新 series INDEX
    if args.series:
        append_to_series_index(column_root, args.series, args.slug, title, today)

    # 成功输出（machine-readable + human）
    print(f"✅ Created articles/{args.slug}/ARTICLE.md")
    print(f"   title: {title}")
    print(f"   type: {args.article_type}")
    print(f"   platforms: {', '.join(platforms)}")
    if args.from_inbox:
        print(f"   from inbox: {args.from_inbox} (moved to inbox/done/)")
    if args.series:
        print(f"   series: {args.series} (appended to INDEX.md)")
    print(f"   STATE.md: row added to ## Active Articles")
    print(f"\n👉 Next: /szw-discuss {args.slug}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
