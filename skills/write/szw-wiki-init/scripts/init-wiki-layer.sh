#!/usr/bin/env bash
#
# init-wiki-layer.sh — 在已有 szw Column 内建立 wiki 层目录子树。
#
# 用法:
#   ./init-wiki-layer.sh [--target DIR]
#
# 参数:
#   --target DIR  Column 根目录（默认 cwd）
#
# 退出码:
#   0  成功
#   1  参数错误
#   3  目标目录不可写
#   4  非 szw Column（.zero/ 不存在）
#
# 设计:
#   - 仅创建 wiki 相关子目录 + .gitkeep（不动 fan.md §9 原 13 目录）
#   - 已存在的目录保持不动（mkdir -p 幂等）
#   - 不渲染任何 schema 文件（那是 SKILL.md 的事）

set -euo pipefail

TARGET=""

while [ $# -gt 0 ]; do
  case "$1" in
    --target)
      TARGET="$2"
      shift 2
      ;;
    --help|-h)
      grep '^#' "$0" | sed 's/^# \?//'
      exit 0
      ;;
    *)
      echo "ERROR: unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

TARGET="${TARGET:-$(pwd)}"

if command -v realpath >/dev/null 2>&1; then
  TARGET=$(realpath "$TARGET")
else
  TARGET=$(cd "$TARGET" 2>/dev/null && pwd)
fi

if [ -z "$TARGET" ] || [ ! -d "$TARGET" ]; then
  echo "ERROR: target dir not found: $TARGET" >&2
  exit 1
fi

if [ ! -w "$TARGET" ]; then
  echo "ERROR: target dir not writable: $TARGET" >&2
  exit 3
fi

if [ ! -d "$TARGET/.zero" ]; then
  echo "ERROR: not a szw Column ($TARGET/.zero/ missing)" >&2
  echo "Run /szw-init first to initialize Column structure." >&2
  exit 4
fi

# Wiki 层目录列表
WIKI_DIRS=(
  "inbox/sources"
  "resources"
  "assets"
  "wiki/concepts"
  "wiki/people"
  "wiki/topics"
  "wiki/frameworks"
  "wiki/tools"
  "wiki/connections"
  "wiki/hubs"
  ".zero/wiki-cache"
)

# 报告已存在的目录
existing=()
created=()

for dir in "${WIKI_DIRS[@]}"; do
  if [ -d "$TARGET/$dir" ]; then
    existing+=("$dir")
  else
    created+=("$dir")
  fi
done

# 创建（mkdir -p 是幂等的）
for dir in "${WIKI_DIRS[@]}"; do
  mkdir -p "$TARGET/$dir"
  # 仅在空目录加 .gitkeep（避免重复 touch）
  if [ -z "$(ls -A "$TARGET/$dir" 2>/dev/null)" ]; then
    touch "$TARGET/$dir/.gitkeep"
  fi
done

# 输出报告
echo "✅ Wiki layer initialized at: $TARGET"
echo ""

if [ ${#created[@]} -gt 0 ]; then
  echo "Created (${#created[@]}):"
  printf '  + %s\n' "${created[@]}"
  echo ""
fi

if [ ${#existing[@]} -gt 0 ]; then
  echo "Already existed (${#existing[@]}, preserved):"
  printf '  = %s\n' "${existing[@]}"
  echo ""
fi

cat <<EOF
Total: ${#WIKI_DIRS[@]} wiki directories ready.

Next (handled by szw-wiki-init SKILL):
  - Render wiki/CONVENTIONS.md and WORKFLOWS.md (always)
  - Render wiki/INDEX.md, log.md, 7 category INDEX.md (unless --bootstrap=skip)
  - Render resources/INDEX.md
  - Update .zero/szw-config.json: wiki.enabled = true
EOF
