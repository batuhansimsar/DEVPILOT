"""Read-only Cargo.toml dependency-name extraction without resolving versions."""

from __future__ import annotations

import re

_GROUPS = frozenset({'dependencies', 'dev-dependencies', 'build-dependencies'})
# Cargo also supports TOML dotted keys (e.g. serde.version = "1").
# Only the first key represents the dependency package name.
_DEPENDENCY = re.compile(
    r'''^\s*(?:"([A-Za-z0-9_-]+)"|'([A-Za-z0-9_-]+)'|([A-Za-z0-9_-]+))'''
    r'''(?:\s*\.\s*(?:"[A-Za-z0-9_-]+"|'[A-Za-z0-9_-]+'|[A-Za-z0-9_-]+))*\s*=\s*(?=\S)'''
)
_NAME = re.compile(r'[A-Za-z0-9_-]+\Z')


def _without_multiline_strings(line: str, multiline: str | None) -> tuple[str, str | None]:
    """Mask TOML multiline string contents, including fake table headers.

    Keep the text outside the string so a dependency assigned a multiline
    string remains visible. An opening delimiter may occur anywhere in the
    line, including after an assignment or in an unrelated metadata value.
    """
    result: list[str] = []
    quote = ''
    escaped = False
    index = 0
    while index < len(line):
        if multiline:
            if line.startswith(multiline, index) and not escaped:
                multiline = None
                index += 3
                continue
            if multiline == '"""' and line[index] == '\\':
                escaped = not escaped
            else:
                escaped = False
            index += 1
            continue
        char = line[index]
        if quote:
            result.append(char)
            if quote == '"' and escaped:
                escaped = False
            elif quote == '"' and char == '\\':
                escaped = True
            elif char == quote:
                quote = ''
            index += 1
            continue
        delimiter = next((item for item in ('"""', "'''") if line.startswith(item, index)), None)
        if delimiter:
            multiline = delimiter
            escaped = False
            index += 3
            continue
        if char == '#':
            result.append(line[index:])
            break
        result.append(char)
        if char in ('"', "'"):
            quote = char
        index += 1
    return ''.join(result), multiline


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


def _header_sections(header: str) -> list[str] | None:
    """Split table keys on unquoted dots (e.g. cfg(feature = "a.b"))."""
    sections: list[str] = []
    quote = ''
    escaped = False
    start = 0
    for index, char in enumerate(header):
        if quote:
            if escaped:
                escaped = False
            elif quote == '"' and char == '\\':
                escaped = True
            elif char == quote:
                quote = ''
        elif char in ('"', "'"):
            quote = char
        elif char == '.':
            section = header[start:index].strip()
            if not section:
                return None
            if len(section) >= 2 and section[0] == section[-1] and section[0] in ('"', "'"):
                section = section[1:-1]
            sections.append(section)
            start = index + 1
    if quote:
        return None
    section = header[start:].strip()
    if not section:
        return None
    if len(section) >= 2 and section[0] == section[-1] and section[0] in ('"', "'"):
        section = section[1:-1]
    sections.append(section)
    return sections


def parse_cargo_dependencies(content: str) -> dict[str, list[str]]:
    """List Cargo dependency names from inline and table-style declarations.

    Supports ``[dependencies]``/``[dependencies.foo]`` and equivalent
    target-specific, workspace, build and dev dependency sections. Bare, quoted and TOML dotted keys are accepted. Multiline string bodies are ignored, so
    embedded table-like text cannot invent dependency names. Never includes
    version specifications or credentials in the output.
    """
    found: dict[str, set[str]] = {}
    active_group = ''
    multiline: str | None = None
    # Mirror scanner decoding for direct UTF-8-SIG text callers.
    for raw in content.removeprefix('\ufeff').splitlines():
        masked, multiline = _without_multiline_strings(raw, multiline)
        line = _without_comment(masked).strip()
        if line.startswith('['):
            header = _table_header(line)
            # An unrecognized table must not keep the previous active group.
            if header is None:
                active_group = ''
                continue
            sections = _header_sections(header)
            active_group = ''
            if not sections:
                continue
            group = ''
            name = ''
            if sections[0] in _GROUPS and len(sections) in (1, 2):
                group = sections[0]
                if len(sections) == 2:
                    name = sections[1]
            elif sections[0] == 'workspace' and len(sections) in (2, 3) and sections[1] in _GROUPS:
                group = sections[1]
                if len(sections) == 3:
                    name = sections[2]
            elif sections[0] == 'target' and len(sections) in (3, 4) and sections[2] in _GROUPS:
                group = sections[2]
                if len(sections) == 4:
                    name = sections[3]
            if name:
                if _NAME.fullmatch(name):
                    found.setdefault(group, set()).add(name)
            elif group:
                active_group = group
            continue
        if active_group:
            match = _DEPENDENCY.match(line)
            if match:
                found.setdefault(active_group, set()).add(next(part for part in match.groups() if part is not None))
    return {group: sorted(names) for group, names in found.items()}
