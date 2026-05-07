"""
frontmatter.py — Minimal YAML frontmatter parser for vault & szw markdown files.

Why custom (not yaml package):
  - macOS system python3 may not have PyYAML installed
  - Avoids extra dep for users
  - Vault frontmatter schema is simple enough (no nesting, no anchors, no flow merges)

Supports:
  - Scalars: key: "value" / key: 'value' / key: value / key: 123 / key: true|false
  - Inline arrays: key: [a, b, c]
  - Block arrays:
      key:
        - item1
        - item2
  - Comments after #
  - Empty lines

Limitations:
  - No nested mappings inside arrays
  - No multi-line strings (> | <)
  - No anchors / aliases
  - No flow mappings ({a: b})

If the user's frontmatter exceeds these, fall back to PyYAML by setting
USE_YAML=1 env var (parse_frontmatter() then imports yaml lazily).
"""

import os
import re


_FM_BOUND_RE = re.compile(r'^---\s*$', re.MULTILINE)


def split_frontmatter(content: str):
    """Split markdown content into (frontmatter_str, body).

    Returns ('', content) when no frontmatter present.
    """
    if not content.startswith('---\n') and not content.startswith('---\r\n'):
        return '', content

    # Find closing --- on its own line, after the opening one
    body_start = content.find('\n---\n', 4)
    if body_start == -1:
        body_start = content.find('\n---\r\n', 4)
        if body_start == -1:
            return '', content
        body_offset = body_start + 6
    else:
        body_offset = body_start + 5

    fm = content[4:body_start]
    body = content[body_offset:]
    return fm, body


def _parse_scalar(value: str):
    """Parse a scalar string into Python type."""
    value = value.strip()
    if not value:
        return ''

    # Strip inline comment unless inside quotes
    if not (value.startswith('"') or value.startswith("'") or value.startswith('[')):
        if '#' in value:
            # Trailing comment
            value = value.split('#', 1)[0].strip()
            if not value:
                return ''

    # Quoted strings
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        return value[1:-1]

    # Booleans
    if value in ('true', 'True', 'TRUE'):
        return True
    if value in ('false', 'False', 'FALSE'):
        return False
    if value in ('null', 'Null', 'NULL', '~'):
        return None

    # Integer
    if re.fullmatch(r'-?\d+', value):
        return int(value)

    # Float
    if re.fullmatch(r'-?\d+\.\d+', value):
        return float(value)

    # Bare string (incl. dates like 2026-04-10)
    return value


def _parse_inline_array(value: str):
    """Parse '[a, b, c]' style array."""
    inner = value.strip()[1:-1].strip()
    if not inner:
        return []
    items = []
    # Naive split by comma; doesn't handle nested commas in strings well,
    # but vault tags / wiki_pages don't contain commas
    for item in inner.split(','):
        items.append(_parse_scalar(item.strip()))
    return items


def _parse_minimal(fm_str: str):
    """Parse frontmatter using minimal custom parser."""
    metadata = {}
    current_key = None
    current_array = None
    indent_match = None

    lines = fm_str.split('\n')
    for line in lines:
        # Strip trailing CR
        line = line.rstrip('\r')

        # Blank line
        if not line.strip():
            continue

        # Block array continuation
        m = re.match(r'^(\s+)-\s*(.*)$', line)
        if m and current_array is not None:
            indent = m.group(1)
            value = m.group(2)
            current_array.append(_parse_scalar(value))
            continue

        # New key (no leading whitespace)
        m = re.match(r'^(\w[\w-]*)\s*:\s*(.*)$', line)
        if m:
            key = m.group(1)
            value = m.group(2).rstrip()

            # Reset block array tracking
            current_key = key
            current_array = None

            if not value:
                # Block array start (next lines are - items) OR empty value
                metadata[key] = []
                current_array = metadata[key]
            elif value.startswith('[') and value.endswith(']'):
                metadata[key] = _parse_inline_array(value)
            else:
                metadata[key] = _parse_scalar(value)
        # else: skip unparseable lines (e.g. malformed)

    # Clean up empty arrays that ended up unfilled (might be empty by intent)
    return metadata


def _parse_with_yaml(fm_str: str):
    import yaml
    return yaml.safe_load(fm_str) or {}


def parse_frontmatter(content: str):
    """Parse markdown content's YAML frontmatter.

    Returns (metadata: dict, body: str).
    Empty frontmatter or no frontmatter → ({}, content).
    """
    fm_str, body = split_frontmatter(content)
    if not fm_str.strip():
        return {}, body

    use_yaml = os.environ.get('USE_YAML', '').lower() in ('1', 'true', 'yes')
    if use_yaml:
        try:
            return _parse_with_yaml(fm_str) or {}, body
        except Exception:
            pass

    return _parse_minimal(fm_str), body


def render_frontmatter(metadata: dict, body: str = '') -> str:
    """Render metadata + body back to markdown frontmatter format.

    Preserves field order based on dict insertion order.
    """
    if not metadata:
        return body

    lines = ['---']
    for key, value in metadata.items():
        if isinstance(value, list):
            if not value:
                lines.append(f'{key}: []')
            elif all(isinstance(x, (str, int, float, bool)) and
                     (not isinstance(x, str) or len(x) < 40 and ',' not in x)
                     for x in value):
                # Short enough → inline
                items_str = ', '.join(_render_scalar(x) for x in value)
                lines.append(f'{key}: [{items_str}]')
            else:
                lines.append(f'{key}:')
                for item in value:
                    lines.append(f'  - {_render_scalar(item)}')
        elif isinstance(value, bool):
            lines.append(f'{key}: {"true" if value else "false"}')
        elif value is None:
            lines.append(f'{key}: null')
        else:
            lines.append(f'{key}: {_render_scalar(value)}')

    lines.append('---')
    fm_block = '\n'.join(lines)
    if body and not body.startswith('\n'):
        return fm_block + '\n' + body
    return fm_block + body


def _render_scalar(value):
    """Render a scalar Python value back to YAML."""
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    # Quote if contains special chars or starts with special prefix
    needs_quote = (
        ':' in s or
        '#' in s or
        s.startswith(('!', '&', '*', '?', '|', '>', '[', ']', '{', '}',
                      ',', '"', "'", '%', '@', '`')) or
        s.strip() != s
    )
    if needs_quote:
        # Use double quotes, escape internal double quotes
        escaped = s.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    return s
