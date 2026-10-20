"""Bounded, read-only discovery of multi-project repositories."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .core import SKIP_DIRS
from .walk import walk_project

WORKSPACE_FILES = {
    'package.json': 'Node.js',
    'pnpm-workspace.yaml': 'Node.js',
    'deno.json': 'Deno',
    'deno.jsonc': 'Deno',
    'pyproject.toml': 'Python',
    'requirements.txt': 'Python',
    'setup.py': 'Python',
    'Pipfile': 'Python',
    'go.mod': 'Go',
    'go.work': 'Go',
    'Cargo.toml': 'Rust',
    'pom.xml': 'Java',
    'build.gradle': 'Java',
    'build.gradle.kts': 'Java',
    'settings.gradle': 'Java',
    'settings.gradle.kts': 'Java',
    'CMakeLists.txt': 'C/C++',
    'CMakePresets.json': 'C/C++',
    'meson.build': 'C/C++',
    'Gemfile': 'Ruby',
    'composer.json': 'PHP',
    'Package.swift': 'Swift',
    'pubspec.yaml': 'Dart',
    'mix.exs': 'Elixir',
    'Dockerfile': 'Docker',
    'Containerfile': 'Docker',
    'compose.yml': 'Docker',
    'compose.yaml': 'Docker',
    'docker-compose.yml': 'Docker',
    'docker-compose.yaml': 'Docker',
}
DOTNET_SUFFIXES = {'.csproj', '.fsproj', '.vbproj', '.sln', '.slnx'}


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
    problems: list[str] = []
    for directory, folders, files in walk_project(root, problems):
        current = Path(directory)
        relative = current.relative_to(root)
        depth = len(relative.parts)
        visited += 1
        if visited > max_directories:
            truncated = True
            break
        candidates = sorted(
            d for d in folders
            if d not in SKIP_DIRS and not (current / d).is_symlink()
        )
        if depth >= max_depth:
            # Only report truncation when a traversable subtree was excluded.
            if candidates:
                truncated = True
            folders[:] = []
        else:
            folders[:] = candidates
        manifests: list[dict[str, str]] = []
        for filename in sorted(files):
            path = current / filename
            if path.is_symlink() or not path.is_file():
                continue
            ecosystem = WORKSPACE_FILES.get(filename)
            if not ecosystem and filename.startswith(('Dockerfile.', 'Containerfile.')):
                ecosystem = 'Docker'
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
        'truncated': truncated or bool(problems),
        'problems': problems,
    }
