"""Read-only Go module requirement parsing for dependency inventories."""

from __future__ import annotations

import ast
import re

# Go module path elements accept '+' and '~' in addition to letters, digits,
# dots, underscores and hyphens. Go's modfile syntax is broader than package
# identifiers; excluding these characters drops valid dependencies.
# Paths with just one element (e.g. example.com) are valid too.
# Go also permits double-quoted module paths and versions in require declarations.
_MODULE_PATH = re.compile(r'[A-Za-z0-9_.+~-]+(?:/[A-Za-z0-9_.+~-]+)*\Z')
_GO_QUOTED_CONTENT = re.compile(
    r'(?:[^"\\]|\\(?:[abfnrtv\\"]|[0-7]{3}|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}))*\Z'
)
_REQUIREMENT = re.compile(
    r'(?:(?P<plain>[A-Za-z0-9_.+~-]+(?:/[A-Za-z0-9_.+~-]+)*)|'
    r'"(?P<quoted>(?:[^"\\]|\\.)*)")\s+'
    r'(?P<version_quote>"?)v[^\s"]+(?P=version_quote)\Z'
)


def parse_go_requirements(content: str) -> list[str]:
    """Collect dependencies in single-line and parenthesized require blocks.

    Go permits whitespace and double-quoted strings with Go-style escapes.
    Only require declarations are included: replace and exclude do not describe
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
            module = match.group('plain')
            if module is None:
                quoted = match.group('quoted')
                if not _GO_QUOTED_CONTENT.fullmatch(quoted):
                    continue
                try:
                    # Decode only string literals; never evaluate expressions.
                    module = ast.literal_eval('"' + quoted + '"')
                except (SyntaxError, ValueError, UnicodeError):
                    continue
            if _MODULE_PATH.fullmatch(module):
                names.add(module)
    return sorted(names)
