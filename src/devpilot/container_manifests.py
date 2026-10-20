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
_IGNORED_SUFFIXES = ('.bak', '.backup', '.tmp', '.swp', '.swo', '.old', '.orig', '.save', '~', '.dockerignore')


# Vim may rotate through .swp, .swo, ..., .swa when previous swaps exist.
# Such editor state files must not be interpreted as named build recipes.
_VIM_SWAP_SUFFIX = re.compile(r'\.sw[a-p]\Z', re.IGNORECASE)



def is_container_manifest(filename: str) -> bool:
    """Recognize build files and named Compose manifests without backup files.

    Match exact case, as project discovery also runs on case-sensitive systems.
    The caller is responsible for accepting only regular, non-symlinked files.
    """
    if filename.casefold().endswith(_IGNORED_SUFFIXES) or _VIM_SWAP_SUFFIX.search(filename):
        return False
    return (filename in _CONTAINER_MANIFESTS
            or _NAMED_COMPOSE.fullmatch(filename) is not None
            or _NAMED_BUILD.fullmatch(filename) is not None)
