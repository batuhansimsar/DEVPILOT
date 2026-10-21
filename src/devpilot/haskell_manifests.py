"""Recognize Cabal and Stack project manifests without opening their contents."""

from __future__ import annotations

import re

_HASKELL_MARKERS = frozenset({
    'cabal.project',
    'cabal.project.freeze',
    'stack.yaml',
    'stack.yaml.lock',
})
_CABAL_PACKAGE = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.cabal\Z', re.ASCII)


def is_haskell_manifest(filename: str) -> bool:
    """Recognize unambiguous Haskell markers, not backups or lookalikes.

    A Cabal package manifest uses a nonempty ASCII alphanumeric/hyphen
    package name. Match the complete filename so copies such as
    'lib.cabal.bak' do not create phantom workspaces.
    """
    return isinstance(filename, str) and (
        filename in _HASKELL_MARKERS or _CABAL_PACKAGE.fullmatch(filename) is not None
    )
