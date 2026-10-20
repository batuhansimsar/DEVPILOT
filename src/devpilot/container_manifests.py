"""Shared Docker/Podman manifest filename recognition for project discovery."""

from __future__ import annotations

import re

# Treat image build files and Compose manifests as project markers without
# opening or executing anything in the inspected repository.
_CONTAINER_MANIFESTS = frozenset({
    'Dockerfile', 'Containerfile',
    'compose.yml', 'compose.yaml',
    'docker-compose.yml', 'docker-compose.yaml',
})
# Named build recipes use non-empty, filename-safe variant components. The
# previous prefix-only check accepted malformed names like Dockerfile..dev.
_NAMED_BUILD = re.compile(
    r'(?:Dockerfile|Containerfile)\.[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\Z'
)
# Require non-empty name segments: compose.dev..yaml is not a valid layer.
_NAMED_COMPOSE = re.compile(
    r'(?:docker-)?compose\.[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\.ya?ml\Z'
)
# JetBrains safe-write files can look like named Dockerfiles because underscores
# are valid variant characters. Never treat these editor temporary copies as
# genuine container manifests.
_IGNORED_SUFFIXES = (
    '.bak', '.backup', '.tmp', '.swp', '.swo', '.old', '.orig', '.save',
    '~', '.dockerignore', '.___jb_tmp___', '.___jb_old___',
)


# Vim rotates swap files through .swp .. .swa, then .svz .. .sva, down to
# .saa when earlier names are taken. All these are temporary editor files,
# not named Dockerfile/Containerfile variants. .swq and .swz are not swaps.
_VIM_SWAP_SUFFIX = re.compile(r'\.s(?:w[a-p]|[a-v][a-z])\Z', re.IGNORECASE)


def is_container_manifest(filename: str) -> bool:
    """Recognize build files and named Compose manifests without backup files.

    Match exact case, as project discovery also runs on case-sensitive systems.
    The caller is responsible for accepting only regular, non-symlinked files.
    """
    if not isinstance(filename, str):
        return False
    if filename.casefold().endswith(_IGNORED_SUFFIXES) or _VIM_SWAP_SUFFIX.search(filename):
        return False
    return (filename in _CONTAINER_MANIFESTS
            or _NAMED_COMPOSE.fullmatch(filename) is not None
            or _NAMED_BUILD.fullmatch(filename) is not None)
