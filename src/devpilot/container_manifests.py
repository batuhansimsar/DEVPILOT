"""Shared Docker/Podman manifest filename recognition for project discovery."""

from __future__ import annotations

# Treat image build files and Compose manifests as project markers without
# opening or executing anything in the inspected repository.
_CONTAINER_MANIFESTS = frozenset({
    'Dockerfile', 'Containerfile',
    'compose.yml', 'compose.yaml',
    'docker-compose.yml', 'docker-compose.yaml',
})
_BUILD_FILE_PREFIXES = ('Dockerfile.', 'Containerfile.')


def is_container_manifest(filename: str) -> bool:
    """Recognize root-level container manifests, including named build files.

    Match exact case, as project discovery also runs on case-sensitive systems.
    The caller is responsible for accepting only regular, non-symlinked files.
    """
    return filename in _CONTAINER_MANIFESTS or filename.startswith(_BUILD_FILE_PREFIXES)
