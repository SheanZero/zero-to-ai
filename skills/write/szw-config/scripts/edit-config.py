#!/usr/bin/env python3
"""
edit-config.py — 读取 / 修改 / 验证 .zero/szw-config.json

用法:
  ./edit-config.py show                                      # 显示当前完整配置
  ./edit-config.py get <dotted.path>                         # 读取单个字段（如 model_profile / hooks.pre_tool_use）
  ./edit-config.py set <dotted.path> <value>                 # 修改字段（带类型 / 取值校验）
  ./edit-config.py validate                                  # 仅验证 schema，不修改
  ./edit-config.py reset <dotted.path>                       # 重置某字段为默认值

退出码:
  0  成功
  1  config 文件不存在（提示先 /szw-init）
  2  路径错误（字段不存在 / 不可达）
  3  取值非法（不在 enum / 类型不匹配）
  4  JSON 解析失败

设计原则:
  - 永远从磁盘读最新版本，写入前用 ASCII-safe JSON 重写（保持稳定 diff）
  - 修改前 schema 校验，避免写入坏配置
  - 不破坏未知字段（向前兼容：旧版本 config 升级后保留新字段）
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# ---------- Schema 定义 ----------

# 各字段的合法值（None 表示任意类型）
SCHEMA: dict[str, Any] = {
    "version": {"type": str, "default": "1.0"},
    "model_profile": {
        "type": str,
        "enum": ["quality", "balanced", "budget", "inherit"],
        "default": "balanced",
    },
    "writing_lang": {"type": str, "enum": ["zh", "en", "mixed"], "default": "zh"},
    "default_platforms": {
        "type": list,
        "item_enum": ["blog", "wechat", "x", "xhs"],
        "default": ["blog", "wechat"],
    },
    "hooks.pre_tool_use": {"type": bool, "default": True},
    "hooks.post_tool_use": {"type": bool, "default": True},
    "hooks.stop": {"type": bool, "default": True},
    "subagents.evidence_researcher": {
        "type": str,
        "enum": ["codex", "claude", "gemini"],
        "default": "codex",
    },
    "subagents.claim_diagnoser": {
        "type": str,
        "enum": ["codex", "claude", "gemini"],
        "default": "codex",
    },
    "subagents.skeptical_reviewer": {
        "type": str,
        "enum": ["codex", "claude", "gemini"],
        "default": "codex",
    },
    "limits.review_revision_max": {"type": int, "min": 1, "max": 5, "default": 2},
    "limits.diagnose_revision_max": {"type": int, "min": 1, "max": 5, "default": 2},
    "limits.quick_word_limit": {"type": int, "min": 200, "max": 3000, "default": 800},
    "style_capture.enabled": {"type": bool, "default": True},
    "style_capture.diff_threshold_pct": {
        "type": int,
        "min": 0,
        "max": 100,
        "default": 5,
    },
    "style_capture.merge_after_n_reviews": {
        "type": int,
        "min": 1,
        "max": 100,
        "default": 10,
    },
    "style_capture.min_pattern_frequency": {
        "type": int,
        "min": 1,
        "max": 50,
        "default": 3,
    },
    "gates.block_draft_on_missing_brief": {"type": bool, "default": True},
    "gates.block_publish_on_missing_review": {"type": bool, "default": True},
    "gates.auto_archive_grill_failed": {"type": bool, "default": False},
}


CONFIG_REL_PATH = ".zero/szw-config.json"


# ---------- 工具函数 ----------


def find_config(start: Path) -> Path:
    """从 cwd 向上找到含 .zero/szw-config.json 的目录"""
    cur = start.resolve()
    while True:
        candidate = cur / CONFIG_REL_PATH
        if candidate.exists():
            return candidate
        if cur.parent == cur:
            break
        cur = cur.parent
    raise FileNotFoundError(
        f"szw-config.json not found in {start} or any parent directory.\n"
        "Run /szw-init first to initialize a column."
    )


def load_config(path: Path) -> dict:
    try:
        with path.open() as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: failed to parse {path}: {e}", file=sys.stderr)
        sys.exit(4)


def save_config(path: Path, data: dict) -> None:
    with path.open("w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def get_nested(data: dict, dotted_path: str) -> Any:
    cur = data
    for part in dotted_path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise KeyError(dotted_path)
        cur = cur[part]
    return cur


def set_nested(data: dict, dotted_path: str, value: Any) -> None:
    parts = dotted_path.split(".")
    cur = data
    for part in parts[:-1]:
        if part not in cur or not isinstance(cur[part], dict):
            cur[part] = {}
        cur = cur[part]
    cur[parts[-1]] = value


def coerce_value(raw: str, expected_type: type) -> Any:
    """字符串 → 期望类型"""
    if expected_type is bool:
        if raw.lower() in ("true", "yes", "1", "on"):
            return True
        if raw.lower() in ("false", "no", "0", "off"):
            return False
        raise ValueError(f"cannot parse bool: {raw}")
    if expected_type is int:
        return int(raw)
    if expected_type is list:
        # 逗号分隔
        return [item.strip() for item in raw.split(",") if item.strip()]
    return raw  # str


def validate_value(dotted_path: str, value: Any) -> None:
    """按 SCHEMA 校验"""
    if dotted_path not in SCHEMA:
        # 不在 schema 中也允许（向前兼容自定义字段），但发出警告
        print(
            f"WARN: '{dotted_path}' not in schema, accepting as-is.", file=sys.stderr
        )
        return

    spec = SCHEMA[dotted_path]
    expected_type = spec["type"]

    if not isinstance(value, expected_type):
        raise TypeError(
            f"{dotted_path} expects {expected_type.__name__}, got {type(value).__name__}"
        )

    if "enum" in spec and value not in spec["enum"]:
        raise ValueError(
            f"{dotted_path} must be one of {spec['enum']}, got {value!r}"
        )

    if "item_enum" in spec and isinstance(value, list):
        bad = [item for item in value if item not in spec["item_enum"]]
        if bad:
            raise ValueError(
                f"{dotted_path} items must be in {spec['item_enum']}, got {bad}"
            )

    if "min" in spec and value < spec["min"]:
        raise ValueError(f"{dotted_path} must be >= {spec['min']}, got {value}")

    if "max" in spec and value > spec["max"]:
        raise ValueError(f"{dotted_path} must be <= {spec['max']}, got {value}")


# ---------- 命令处理 ----------


def cmd_show(config_path: Path) -> int:
    data = load_config(config_path)
    print(f"# {config_path}\n")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


def cmd_get(config_path: Path, dotted_path: str) -> int:
    data = load_config(config_path)
    try:
        value = get_nested(data, dotted_path)
    except KeyError:
        print(f"ERROR: path '{dotted_path}' not found in config", file=sys.stderr)
        return 2
    if isinstance(value, (dict, list)):
        print(json.dumps(value, indent=2, ensure_ascii=False))
    else:
        print(value)
    return 0


def cmd_set(config_path: Path, dotted_path: str, raw_value: str) -> int:
    data = load_config(config_path)

    # 先用 schema 推断类型
    if dotted_path in SCHEMA:
        try:
            value = coerce_value(raw_value, SCHEMA[dotted_path]["type"])
        except (ValueError, TypeError) as e:
            print(f"ERROR: type coercion failed: {e}", file=sys.stderr)
            return 3
    else:
        # 未知字段：尝试 JSON 解析，失败则当字符串
        try:
            value = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value

    try:
        validate_value(dotted_path, value)
    except (ValueError, TypeError) as e:
        print(f"ERROR: validation failed: {e}", file=sys.stderr)
        return 3

    old = None
    try:
        old = get_nested(data, dotted_path)
    except KeyError:
        pass

    set_nested(data, dotted_path, value)
    save_config(config_path, data)
    print(f"✅ {dotted_path}: {old!r} → {value!r}")
    print(f"   saved to {config_path}")
    return 0


def cmd_validate(config_path: Path) -> int:
    data = load_config(config_path)
    errors: list[str] = []
    for dotted_path in SCHEMA:
        try:
            value = get_nested(data, dotted_path)
            validate_value(dotted_path, value)
        except KeyError:
            errors.append(f"  - {dotted_path}: MISSING (will use default)")
        except (ValueError, TypeError) as e:
            errors.append(f"  - {dotted_path}: {e}")

    if errors:
        print("Validation issues:")
        for err in errors:
            print(err)
        return 3 if any("MISSING" not in e for e in errors) else 0
    print("✅ Config valid (all known fields conform to schema)")
    return 0


def cmd_reset(config_path: Path, dotted_path: str) -> int:
    if dotted_path not in SCHEMA:
        print(
            f"ERROR: '{dotted_path}' not in schema; cannot reset (no default known)",
            file=sys.stderr,
        )
        return 2
    default = SCHEMA[dotted_path]["default"]
    data = load_config(config_path)
    old = None
    try:
        old = get_nested(data, dotted_path)
    except KeyError:
        pass
    set_nested(data, dotted_path, default)
    save_config(config_path, data)
    print(f"✅ {dotted_path}: {old!r} → {default!r} (default)")
    return 0


# ---------- main ----------


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1

    try:
        config_path = find_config(Path.cwd())
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    cmd = argv[1]
    args = argv[2:]

    if cmd == "show" and not args:
        return cmd_show(config_path)
    if cmd == "get" and len(args) == 1:
        return cmd_get(config_path, args[0])
    if cmd == "set" and len(args) == 2:
        return cmd_set(config_path, args[0], args[1])
    if cmd == "validate" and not args:
        return cmd_validate(config_path)
    if cmd == "reset" and len(args) == 1:
        return cmd_reset(config_path, args[0])

    print(f"ERROR: unknown command or wrong arguments: {cmd} {args}", file=sys.stderr)
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
