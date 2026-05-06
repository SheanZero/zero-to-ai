#!/usr/bin/env python3
"""Validate a trigger eval set.

Expected JSON shape:
[
  {"query": "...", "should_trigger": true},
  {"query": "...", "should_trigger": false}
]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def validate(path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not path.exists():
        return {"ok": False, "errors": [f"File not found: {path}"], "warnings": []}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"ok": False, "errors": [f"Invalid JSON: {exc}"], "warnings": []}

    if not isinstance(data, list):
        return {"ok": False, "errors": ["Trigger eval file must be a JSON array"], "warnings": []}

    pos = 0
    neg = 0
    seen: set[str] = set()

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            errors.append(f"Item {i} must be an object")
            continue
        query = item.get("query")
        should = item.get("should_trigger")
        if not isinstance(query, str) or not query.strip():
            errors.append(f"Item {i} has missing or empty query")
        else:
            qnorm = " ".join(query.lower().split())
            if qnorm in seen:
                warnings.append(f"Duplicate or near-duplicate query at item {i}: {query[:80]!r}")
            seen.add(qnorm)
            if len(query.split()) < 5:
                warnings.append(f"Item {i} query may be too terse to test realistic triggering")
        if not isinstance(should, bool):
            errors.append(f"Item {i} should_trigger must be true or false")
        elif should:
            pos += 1
        else:
            neg += 1

    if len(data) < 12:
        warnings.append(f"Only {len(data)} trigger evals; consider 12–20 for meaningful coverage")
    if pos < 6:
        warnings.append(f"Only {pos} should-trigger queries; consider at least 6")
    if neg < 6:
        warnings.append(f"Only {neg} should-not-trigger queries; consider at least 6")

    return {"ok": not errors, "errors": errors, "warnings": warnings, "total": len(data), "should_trigger": pos, "should_not_trigger": neg}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("trigger_eval_json", help="Path to trigger-evals.json")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    result = validate(Path(args.trigger_eval_json).expanduser())
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        status = "PASS" if result.get("ok") else "FAIL"
        print(f"{status}: {args.trigger_eval_json}")
        print(f"total={result.get('total', 0)} should_trigger={result.get('should_trigger', 0)} should_not_trigger={result.get('should_not_trigger', 0)}")
        for err in result.get("errors", []):
            print(f"ERROR: {err}")
        for warn in result.get("warnings", []):
            print(f"WARN: {warn}")
        if result.get("ok") and not result.get("warnings"):
            print("No issues found.")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
