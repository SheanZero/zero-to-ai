#!/usr/bin/env bash
#
# create-skeleton.sh — 为 szw-init 创建 Column 基础目录骨架
#
# 用法:
#   ./create-skeleton.sh [target_dir]
#
# 参数:
#   target_dir  目标 Column 根目录（默认当前工作目录）
#
# 退出码:
#   0  成功
#   1  参数错误（目标目录不存在）
#   2  目标已存在 .zero/（防覆盖）
#   3  目标目录不可写
#
# 设计:
#   - 仅创建 fan.md §9 的基础目录骨架（13 个）
#   - 不创建 wiki 层目录（resources/ assets/ wiki/{7 类}/ 等）
#     wiki 层由 /szw-wiki-init 调用其自身的 init-wiki-layer.sh 创建
#   - 仅创建目录 + .gitkeep，不写任何业务文件
#   - 业务文件由 szw-init SKILL 通过对话式问答 + 模板渲染生成；
#     CLAUDE.md / AGENTS.md 由 /szw-claude-init 生成

set -euo pipefail

TARGET="${1:-$(pwd)}"

if command -v realpath >/dev/null 2>&1; then
  TARGET=$(realpath "$TARGET")
else
  TARGET=$(cd "$TARGET" 2>/dev/null && pwd)
fi

if [ -z "$TARGET" ] || [ ! -d "$TARGET" ]; then
  echo "ERROR: target dir not found: ${1:-$(pwd)}" >&2
  exit 1
fi

if [ ! -w "$TARGET" ]; then
  echo "ERROR: target dir not writable: $TARGET" >&2
  exit 3
fi

# 防覆盖检查
if [ -d "$TARGET/.zero" ]; then
  cat >&2 <<EOF
ERROR: $TARGET/.zero already exists.

This directory appears already initialized as a Column.
Options:
  - Use /szw-progress to see current state
  - Use /szw-evolve (v3.0) for major repositioning
  - cd to a different empty directory and re-run /szw-init
EOF
  exit 2
fi

# fan.md §9 基础显性子目录
EXPLICIT_DIRS=(
  "published"
  "articles"
  "articles/quick"
  "articles/archived"
  "editorial-adr"
  "glossary"
  "inbox/pending"
  "inbox/done"
  "series"
  "summaries"
)

# fan.md §9 基础隐藏系统目录
HIDDEN_DIRS=(
  ".zero/evidence"
  ".zero/audits"
  ".zero/writing-history"
)

for dir in "${EXPLICIT_DIRS[@]}"; do
  mkdir -p "$TARGET/$dir"
  touch "$TARGET/$dir/.gitkeep"
done

for dir in "${HIDDEN_DIRS[@]}"; do
  mkdir -p "$TARGET/$dir"
  touch "$TARGET/$dir/.gitkeep"
done

cat <<EOF
✅ Column base skeleton created at: $TARGET

Structure:
  ./
  ├── published/             已发布成品
  ├── articles/              文章过程目录
  │   ├── quick/             /szw-quick 产物
  │   └── archived/          弃稿
  ├── editorial-adr/         决策记录
  ├── glossary/              术语
  ├── inbox/                 灵感库
  │   ├── pending/
  │   └── done/
  ├── series/                系列连载
  ├── summaries/             周期汇总
  └── .zero/                 系统状态 + AI 内部
      ├── evidence/
      ├── audits/
      └── writing-history/

Total: $((${#EXPLICIT_DIRS[@]} + ${#HIDDEN_DIRS[@]})) directories with .gitkeep markers.

Next (handled by szw-init SKILL):
  - Deep questioning (Mode A) or content review (Mode B)
  - Generate COLUMN.md / EDITORIAL_CONTEXT.md / ADRs
  - Generate STATE.md and szw-config.json
  - Call /szw-claude-init   → render CLAUDE.md + AGENTS.md
  - (If wiki enabled) call /szw-wiki-init → build wiki layer + render schema

To verify: find . -type d
EOF
