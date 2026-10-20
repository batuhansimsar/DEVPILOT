"""Read-only Go module requirement parsing for dependency inventories."""

from __future__ import annotations

import re

# Go module paths and versions are tokens, not arbitrary user-provided URLs.
_REQUIREMENT = re.compile(r"([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+)\s+(v\S+)\Z")


def parse_go_requirements(content: str) -> list[str]:
    """Collect dependencies in single-line and parenthesized require blocks.

    Go permits tabs and repeated whitespace between directive tokens. Only
    require declarations are included: replace and exclude do not describe
    additional dependencies. Returned data contains names, no versions.
    """
    names: set[str] = set()
    in_require_block = False
    for raw in content.splitlines():
        line = raw.split('//', 1)[0].strip()
        if not line:
            continue
        if in_require_block:
            if line == ')':
                in_require_block = False
                continue
            entry = line
        else:
            fields = line.split(None, 1)
            if len(fields) != 2 or fields[0] != 'require':
                continue
            entry = fields[1].strip()
            if entry == '(':
                in_require_block = True
                continue
        match = _REQUIREMENT.fullmatch(entry)
        if match:
            names.add(match.group(1))
    return sorted(names)
