"""Recognize common pip requirements manifest filenames without reading content."""

from __future__ import annotations

import re

# Require a separator before and a non-empty component after a requirements
# variant (requirements-dev.txt, requirements_test.in, etc.). Prefixes such as
# dev-requirements.txt, test_requirements.in, and local.requirements.in are
# also common. An arbitrary name like requirementsnotes.txt is not a manifest.
_REQUIREMENTS_MANIFEST = re.compile(
    r'(?:requirements(?:[._-][A-Za-z0-9][A-Za-z0-9_-]*)*|'
    r'[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*[._-]requirements)\.(?:txt|in)\Z',
    # Fold ASCII case only; Unicode casefold would accept long-s and Kelvin
    # sign lookalikes that are not valid pip manifest filenames.
    flags=re.IGNORECASE | re.ASCII,
)


# Copies such as requirements.txt.txt are not pip-compatible manifest names;
# otherwise a document accidentally copied with a second suffix can trigger
# Python-project detection and unnecessary dependency scanning.
_DOUBLE_EXTENSION = ('.txt.txt', '.txt.in', '.in.txt', '.in.in')


def is_requirements_manifest(name: str) -> bool:
    """Accept pip and pip-tools filenames without matching unrelated files.

    Supports base manifests, separated variants, and prefixed requirements
    files with hyphen, underscore, or period separators regardless of ASCII
    letter case; rejects empty variants, backups, and Unicode lookalikes.
    """
    if not isinstance(name, str):
        return False
    return (
        not name.lower().endswith(_DOUBLE_EXTENSION)
        and _REQUIREMENTS_MANIFEST.fullmatch(name) is not None
    )
