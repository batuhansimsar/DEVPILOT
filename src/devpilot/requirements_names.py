"""Recognize common pip requirements manifest filenames without reading content."""

from __future__ import annotations

import re

# Bare `requirements` or variants separated by a punctuation character are
# manifests; arbitrary prefixes like `requirementsbackup.txt` are not. Accept
# both pip-tools `.in` inputs and compiled `.txt` files.
_QUALIFIER = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
_REQUIREMENTS_MANIFEST = re.compile(
    rf"(?:requirements(?:[-_.]{_QUALIFIER})?|{_QUALIFIER}[-_.]requirements)\.(?:txt|in)\Z"
)


def is_requirements_manifest(name: str) -> bool:
    """Return whether *name* follows a recognized pip requirements naming form.

    Both `requirements-dev.txt` and `dev-requirements.in` are common. Require
    nonempty variant names and separators so unrelated files cannot turn an
    otherwise non-Python directory into a reported Python workspace.
    """
    return isinstance(name, str) and _REQUIREMENTS_MANIFEST.fullmatch(name) is not None
