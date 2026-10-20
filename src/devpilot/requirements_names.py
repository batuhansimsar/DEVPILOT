"""Recognize common pip requirements manifest filenames without reading content."""

from __future__ import annotations

import re

# Require a separator before and a non-empty component after a requirements
# variant (requirements-dev.txt, requirements_test.in, etc.). Prefixes such as
# dev-requirements.txt are also common. An arbitrary name like
# requirementsnotes.txt is not a pip dependency manifest.
_REQUIREMENTS_MANIFEST = re.compile(
    r'(?:requirements(?:[._-][A-Za-z0-9][A-Za-z0-9_-]*)*|'
    r'[A-Za-z0-9][A-Za-z0-9_-]*-requirements)\.(?:txt|in)\Z'
)


# Copies such as requirements.txt.txt are not pip-compatible manifest names;
# otherwise a document accidentally copied with a second suffix can trigger
# Python-project detection and unnecessary dependency scanning.
_DOUBLE_EXTENSION = ('.txt.txt', '.txt.in', '.in.txt', '.in.in')


def is_requirements_manifest(name: str) -> bool:
    """Accept pip and pip-tools filenames without matching unrelated files.

    Supports base manifests, separated variants, and prefixed requirements
    files regardless of ASCII letter case; rejects empty variants, backups,
    double extensions, and partial word matches.
    """
    if not isinstance(name, str):
        return False
    normalized = name.casefold()
    return (
        not normalized.endswith(_DOUBLE_EXTENSION)
        and _REQUIREMENTS_MANIFEST.fullmatch(normalized) is not None
    )
