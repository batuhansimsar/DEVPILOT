"""Privacy-safe name inventory for pip requirements files.

Never return repository URLs, version pins, index settings or hash values.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from .pyproject_deps import _REQUIREMENT, _canonical, _valid_requirement_suffix

# pip accepts both --hash=algorithm:digest and --hash algorithm:digest.
# Strip one or more options before validating the PEP 508 declaration, while
# keeping all hash material out of the dependency inventory.
_HASH_OPTIONS = re.compile(r'(?:\s+--hash(?:=|\s+)(?:sha256|sha384|sha512):[0-9a-fA-F]+)+\s*\Z')


def _logical_lines(content: str) -> Iterator[str]:
    """Join pip's backslash-continued lines before examining declarations.

    An unterminated continuation is incomplete and must not contribute a
    dependency, even if its first physical line looks like a valid name.
    """
    pieces: list[str] = []
    for raw in content.splitlines():
        line = raw.strip()
        if line.endswith('\\'):
            pieces.append(line[:-1].rstrip())
            continue
        if pieces:
            pieces.append(line)
            yield ' '.join(pieces)
            pieces.clear()
        else:
            yield line



def _logical_lines(content: str):
    """Join pip's unescaped backslash continuations before parsing entries.

    A dangling continuation is incomplete and must not create an inventory
    entry. Accumulate fragments in a list so long, bounded files remain cheap.
    """
    fragments: list[str] = []
    for raw in content.splitlines():
        line = raw.strip()
        if not line and fragments:
            continue
        trailing = len(line) - len(line.rstrip('\\'))
        if trailing % 2:
            fragments.append(line[:-1].rstrip())
            continue
        if fragments:
            fragments.append(line)
            line = ' '.join(fragments)
            fragments.clear()
        yield line


def parse_requirements_dependencies(content: str) -> list[str]:
    """Return canonical names from valid requirement declarations only.

    Ignore pip directives, bare VCS/URL lines and malformed requirements.
    Join pip-style continuations first, including versions, direct references
    and hash options; incomplete trailing entries are ignored.
    """
    names: set[str] = set()
    for line in _logical_lines(content):
        if not line or line.startswith(('#', '-', 'git+', 'https:', 'http:')):
            continue
        # A comment must have whitespace before #; URL fragments are data.
        line = re.split(r'\s+#', line, maxsplit=1)[0].rstrip()
        line = _HASH_OPTIONS.sub('', line).rstrip()
        match = _REQUIREMENT.match(line)
        if match and _valid_requirement_suffix(line[match.end():]):
            names.add(_canonical(match.group(1)))
    return sorted(names)
