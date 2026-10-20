"""Bounded, read-only discovery of multi-project repositories."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .core import SKIP_DIRS

WORKSPACE_FILES = {
    'package.json': 'Node.js',
    'pyproject.toml': 'Python',
    'requirements.txt': 'Python',
    'setup.py': 'Python',
    'go.mod': 'Go',
    'Cargo.toml': 'Rust',
    'pom.xml': 'Java',
    'build.gradle': 'Java',
    'build.gradle.kts': 'Java',
    'Gemfile': 'Ruby',
    'composer.json': 'PHP',
}
DOTNET_SUFFIXES = {'.csproj', '.fsproj', '.sln', '.slnx'}


def discover_workspaces(root: Path, max_depth: int = 5, max_directories: int = 5000) -> dict[str, Any]:
    """Find manifests at root and below without opening files or following symlinks.

    The path is a repository root; all returned paths are relative to it. A cap
    prevents unexpectedly expensive walks across very large monorepos.
    """
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f'Not a directory: {root}')
    if not (0 <= max_depth <= 50 and 1 <= max_directories <= 100000):
        raise ValueError('Invalid scan limits')

    workspaces: list[dict[str, Any]] = []
    visited = 0
    truncated = False
    for directory, folders, files in os.walk(root, followlinks=False):
        current = Path(directory)
        relative = current.relative_to(root)
        depth = len(relative.parts)
        visited += 1
        if visited > max_directories:
            truncated = True
            break
        folders[:] = sorted(
            d for d in folders
            if d not in SKIP_DIRS and depth < max_depth and not (current / d).is_symlink()
        )
        manifests: list[dict[str, str]] = []
        for filename in sorted(files):
            path = current / filename
            if path.is_symlink() or not path.is_file():
                continue
            ecosystem = WORKSPACE_FILES.get(filename)
            if not ecosystem and path.suffix.lower() in DOTNET_SUFFIXES:
                ecosystem = '.NET'
            if ecosystem:
                manifests.append({'file': filename, 'ecosystem': ecosystem})
        if manifests:
            workspaces.append({
                'path': relative.as_posix(),
                'ecosystems': sorted({m['ecosystem'] for m in manifests}),
                'manifests': manifests,
            })

    return {
        'path': str(root),
        'workspaces': workspaces,
        'workspace_count': len(workspaces),
        'directories_scanned': min(visited, max_directories),
        'truncated': truncated,
    }
