"""Recognize Julia project and lock manifests without opening their contents."""

from __future__ import annotations

import re

JULIA_MANIFESTS = frozenset({
    'Project.toml', 'JuliaProject.toml', 'Manifest.toml', 'JuliaManifest.toml',
})
# Julia can select a version-specific manifest for its current minor release.
# Reject ambiguous leading zeros, empty components and editor backup files.
_VERSIONED_MANIFEST = re.compile(
    r'Manifest-v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.toml\Z'
)


def is_julia_manifest(filename: str) -> bool:
    """Identify supported exact Julia manifest filenames and versioned locks."""
    return isinstance(filename, str) and (
        filename in JULIA_MANIFESTS or _VERSIONED_MANIFEST.fullmatch(filename) is not None
    )
