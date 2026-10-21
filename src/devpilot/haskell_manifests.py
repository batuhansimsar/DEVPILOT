"""Identify Haskell project manifests without opening or executing project files."""

from __future__ import annotations

import re

# Stack, hpack and Cabal support these project-level markers. Do not treat
# generic Haskell source files or unrelated build artifacts as project roots.
_HASKELL_MARKERS = frozenset({
    'stack.yaml', 'stack.yaml.lock', 'cabal.project', 'cabal.project.freeze', 'package.yaml',
})
_CABAL_PACKAGE_FILE = re.compile(r'[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*\.cabal\Z')


def is_haskell_manifest(filename: str) -> bool:
    """Match manifest basenames, excluding backups and lookalike suffixes.

    Cabal package names consist of hyphen-separated ASCII alphanumeric
    components. This intentionally rejects hidden, malformed and suffixed
    backup copies rather than treating them as additional workspaces.
    """
    return isinstance(filename, str) and (
        filename in _HASKELL_MARKERS or _CABAL_PACKAGE_FILE.fullmatch(filename) is not None
    )
