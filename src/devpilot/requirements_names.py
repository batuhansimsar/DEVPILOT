"""Recognize common pip requirements manifest filenames without reading content."""

from __future__ import annotations

import re

# Require a separator around each non-empty qualifier component. Projects may
# combine prefix and suffix conventions, e.g. dev-requirements-test.txt, as
# well as using either convention alone. Arbitrary lookalikes such as
# requirementsnotes.txt must not be discovered as pip manifests.
_REQUIREMENTS_MANIFEST = re.compile(
    r'(?:[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*[._-])?'
    r'requirements(?:[._-][A-Za-z0-9]+)*\.(?:txt|in)\Z',
    # Delimiter-separated components avoid exponential regex backtracking on
    # filenames such as requirements-a-a-a-...!.txt.
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

    Supports base manifests, prefix/suffix qualifiers (including both together)
    with hyphen, underscore, or period separators regardless of ASCII letter
    case; rejects empty variants, backups, and Unicode lookalikes.
    """
    if not isinstance(name, str):
        return False
    return (
        not name.lower().endswith(_DOUBLE_EXTENSION)
        and _REQUIREMENTS_MANIFEST.fullmatch(name) is not None
    )
