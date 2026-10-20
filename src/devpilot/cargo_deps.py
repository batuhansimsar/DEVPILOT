"""Read-only Cargo.toml dependency-name extraction without resolving versions."""

from __future__ import annotations

import re

_GROUPS = frozenset({'dependencies', 'dev-dependencies', 'build-dependencies'})
_DEPENDENCY = re.compile(r'''^\s*(?:"([A-Za-z0-9_-]+)"|'([A-Za-z0-9_-]+)'|([A-Za-z0-9_-]+))\s*=''')
_NAME = re.compile(r'[A-Za-z0-9_-]+\Z')


def _without_comment(line: str) -> str:
    """Ignore TOML comments, retaining hashes inside quoted table names.

    Table headers may be followed by comments without whitespace. Splitting at
    the first hash loses legitimate hashes in quoted target expressions.
    """
    quote = ''
    escaped = False
    for index, char in enumerate(line):
        if quote:
            if quote == '"' and escaped:
                escaped = False
            elif quote == '"' and char == '\\':
                escaped = True
            elif char == quote:
                quote = ''
        elif char in ('"', "'"):
            quote = char
        elif char == '#':
            return line[:index]
    return line


def _table_header(line: str) -> str | None:
    """Extract a TOML table name, allowing trailing comments outside quotes."""
    if not line.startswith('[') or line.startswith('[['):
        return None
    quote = ''
    escaped = False
    for index, character in enumerate(line[1:], 1):
        if quote == '"':
            if escaped:
                escaped = False
            elif character == '\\':
                escaped = True
            elif character == '"':
                quote = ''
        elif quote == "'":
            if character == "'":
                quote = ''
        elif character in ("'", '"'):
            quote = character
        elif character == ']':
            trailing = line[index + 1:].strip()
            if not trailing or trailing.startswith('#'):
                return line[1:index]
            return None
    return None


def parse_cargo_dependencies(content: str) -> dict[str, list[str]]:
    """List Cargo dependency names from inline and table-style declarations.

    Supports ``[dependencies]``/``[dependencies.foo]`` and equivalent
    target-specific, workspace, build and dev dependency sections. Bare and
    quoted TOML keys are accepted. Never includes version specifications or credentials in the output.
    """
    found: dict[str, set[str]] = {}
    active_group = ''
    for raw in content.splitlines():
        line = _without_comment(raw).strip()
        if line.startswith('['):
            header = _table_header(line)
            # An unrecognized table must not keep the previous active group.
            if header is None:
                active_group = ''
                continue
            sections = header.split('.')
            allowed_scope = len(sections) == 1 or sections[0] in ('target', 'workspace')
            active_group = sections[-1] if allowed_scope and sections[-1] in _GROUPS else ''
            if len(sections) > 1 and sections[-2] in _GROUPS and (
                    len(sections) == 2 or sections[0] in ('target', 'workspace')):
                name = sections[-1].strip('"\'')
                if _NAME.fullmatch(name):
                    found.setdefault(sections[-2], set()).add(name)
            continue
        # An unsupported or malformed table ends the preceding dependency group.
        if line.startswith('['):
            active_group = ''
            continue
        if active_group:
            match = _DEPENDENCY.match(line)
            if match:
                found.setdefault(active_group, set()).add(next(part for part in match.groups() if part is not None))
    return {group: sorted(names) for group, names in found.items()}
