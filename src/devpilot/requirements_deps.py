"""Privacy-safe name inventory for pip requirements files.

Never return repository URLs, version pins, index settings or hash values.
"""

from __future__ import annotations

import re

from .pyproject_deps import _REQUIREMENT, _canonical, _valid_requirement_suffix

# pip accepts both --hash=algorithm:digest and --hash algorithm:digest.
# Strip one or more options before validating the PEP 508 declaration, while
# keeping all hash material out of the dependency inventory.
_HASH_OPTIONS = re.compile(r'(?:\s+--hash(?:=|\s+)(?:sha256|sha384|sha512):[0-9a-fA-F]+)+\s*\Z')


def parse_requirements_dependencies(content: str) -> list[str]:
    """Return canonical names from valid requirement declarations only.

    Ignore pip directives, bare VCS/URL lines and malformed requirements.
    A backslash on a pinned line may continue pip hash options on later lines;
    the dependency name itself remains on the first line.
    """
    names: set[str] = set()
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith(('#', '-', 'git+', 'https:', 'http:')):
            continue
        # A comment must have whitespace before #; URL fragments are data.
        line = re.split(r'\s+#', line, maxsplit=1)[0].rstrip()
        if line.endswith('\\'):
            line = line[:-1].rstrip()
        line = _HASH_OPTIONS.sub('', line).rstrip()
        match = _REQUIREMENT.match(line)
        if match and _valid_requirement_suffix(line[match.end():]):
            names.add(_canonical(match.group(1)))
    return sorted(names)
