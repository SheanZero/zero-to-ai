#!/usr/bin/env python3
"""Quickly validate a Claude/Codex-style skill folder.

Checks are intentionally lightweight and portable:
- SKILL.md exists
- frontmatter contains name and description
- name is kebab-case
- description is <= 1024 chars
- description contains a clear "Use when" trigger phrase
- SKILL.md is not overly long
- local markdown links point to existing files when possible
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

Kebab = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
Link = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip()
    body = text[end + len("\n---") :]
    data: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data, body


def validate(skill_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.exists():
        return {"ok": False, "errors": ["Missing SKILL.md"], "warnings": []}

    text = skill_md.read_text(encoding="utf-8")
    meta, _body = parse_frontmatter(text)

    name = meta.get("name", "")
    description = meta.get("description", "")

    if not name:
        errors.append("Missing frontmatter field: name")
    elif not Kebab.match(name):
        errors.append(f"Skill name is not kebab-case: {name!r}")

    if not description:
        errors.append("Missing frontmatter field: description")
    else:
        if len(description) > 1024:
            errors.append(f"Description is too long: {len(description)} chars > 1024")
        if "Use when" not in description and "use when" not in description:
            warnings.append("Description does not include an explicit 'Use when' trigger phrase")
        if len(description) < 80:
            warnings.append("Description may be too short to guide triggering clearly")

    line_count = len(text.splitlines())
    if line_count > 500:
        errors.append(f"SKILL.md is very long: {line_count} lines > 500")
    elif line_count > 150:
        warnings.append(f"SKILL.md is {line_count} lines; consider moving rare details to references/")

    for match in Link.finditer(text):
        target = match.group(1).split("#", 1)[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        path = (skill_dir / target).resolve()
        try:
            path.relative_to(skill_dir.resolve())
        except ValueError:
            warnings.append(f"Local link points outside skill directory: {target}")
            continue
        if not path.exists():
            warnings.append(f"Local markdown link does not exist: {target}")

    return {"ok": not errors, "errors": errors, "warnings": warnings, "name": name, "description_chars": len(description), "line_count": line_count}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_dir", help="Path to a skill directory containing SKILL.md")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()

    result = validate(Path(args.skill_dir).expanduser())
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        status = "PASS" if result.get("ok") else "FAIL"
        print(f"{status}: {args.skill_dir}")
        for err in result.get("errors", []):
            print(f"ERROR: {err}")
        for warn in result.get("warnings", []):
            print(f"WARN: {warn}")
        if result.get("ok") and not result.get("warnings"):
            print("No issues found.")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
