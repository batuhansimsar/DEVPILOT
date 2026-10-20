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


def is_requirements_manifest(name: str) -> bool:
    """Accept pip and pip-tools filenames without matching unrelated files.

    Supports base manifests, separated variants, and prefixed requirements
    files; rejects empty variants, backups, and partial word matches.
    """
    return isinstance(name, str) and _REQUIREMENTS_MANIFEST.fullmatch(name) is not None
