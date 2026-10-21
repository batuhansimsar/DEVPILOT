"""Bounded, read-only discovery of multi-project repositories."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from .container_manifests import is_container_manifest
from .dotnet_manifests import DOTNET_SUFFIXES
from .core import SKIP_DIRS
from .walk import walk_project
from .requirements_names import is_requirements_manifest
from .pylock import is_pylock_manifest

WORKSPACE_FILES = {
    'package.json': 'Node.js',
    'package-lock.json': 'Node.js',
    'npm-shrinkwrap.json': 'Node.js',
    'pnpm-lock.yaml': 'Node.js',
    'yarn.lock': 'Node.js',
    'pnpm-workspace.yaml': 'Node.js',
    # Bun's text and legacy binary lockfiles are also package-manager markers.
    'bun.lock': 'Node.js',
    'bun.lockb': 'Node.js',
    'deno.json': 'Deno',
    'deno.jsonc': 'Deno',
    # A lockfile alone identifies Deno even without deno.json or deno.jsonc.
    'deno.lock': 'Deno',
    'pyproject.toml': 'Python',
    'requirements.txt': 'Python',
    'setup.py': 'Python',
    'setup.cfg': 'Python',
    'Pipfile': 'Python',
    'Pipfile.lock': 'Python',
    'uv.lock': 'Python',
    'poetry.lock': 'Python',
    'environment.yml': 'Conda',
    'environment.yaml': 'Conda',
    'go.mod': 'Go',
    'go.work': 'Go',
    'Cargo.toml': 'Rust',
    'Cargo.lock': 'Rust',
    'build.zig': 'Zig',
    'build.zig.zon': 'Zig',
    'pom.xml': 'Java',
    'build.sbt': 'Scala',
    'deps.edn': 'Clojure',
    'project.clj': 'Clojure',
    'build.gradle': 'Java',
    'build.gradle.kts': 'Java',
    'settings.gradle': 'Java',
    'settings.gradle.kts': 'Java',
    'CMakeLists.txt': 'C/C++',
    'CMakePresets.json': 'C/C++',
    'meson.build': 'C/C++',
    'WORKSPACE': 'Bazel',
    'WORKSPACE.bazel': 'Bazel',
    'MODULE.bazel': 'Bazel',
    'Gemfile': 'Ruby',
    'Gemfile.lock': 'Ruby',
    'gems.locked': 'Ruby',
    'gems.rb': 'Ruby',
    'composer.json': 'PHP',
    'composer.lock': 'PHP',
    'Package.swift': 'Swift',
    'Package.resolved': 'Swift',
    'pubspec.yaml': 'Dart',
    'pubspec.lock': 'Dart',
    'mix.exs': 'Elixir',
    'mix.lock': 'Elixir',
    'Project.toml': 'Julia',
    'JuliaProject.toml': 'Julia',
    'Manifest.toml': 'Julia',
    'JuliaManifest.toml': 'Julia',
    # Both flake-based and legacy Nix projects have distinctive root markers.
    # A lockfile alone is enough to identify a flake workspace.
    'flake.nix': 'Nix',
    'flake.lock': 'Nix',
    'shell.nix': 'Nix',
    'default.nix': 'Nix',
    'Directory.Packages.props': '.NET',
    'global.json': '.NET',
    'Dockerfile': 'Docker',
    'Containerfile': 'Docker',
    'compose.yml': 'Docker',
    'compose.yaml': 'Docker',
    'docker-compose.yml': 'Docker',
    'docker-compose.yaml': 'Docker',
}

# Julia selects a version-specific lockfile for its matching minor release.
# Match ASCII numeric versions only; backup files must not be treated as manifests.
_JULIA_VERSIONED_MANIFEST = re.compile(r'Manifest-v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.toml\Z')


def discover_workspaces(root: Path, max_depth: int = 5, max_directories: int = 5000) -> dict[str, Any]:
    """Find manifests at root and below without opening files or following symlinks.

    The path is a repository root; all returned paths are relative to it. A cap
    prevents unexpectedly expensive walks across very large monorepos.
    """
    # Preserve a symlink at the requested root so walk_project can report an
    # incomplete scan rather than following it into another directory.
    root = root.absolute()
    if not root.is_dir():
        raise ValueError(f'Not a directory: {root}')
    if (type(max_depth) is not int or type(max_directories) is not int
            or not (0 <= max_depth <= 50 and 1 <= max_directories <= 100000)):
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
            if not ecosystem and is_requirements_manifest(filename):
                ecosystem = 'Python'
            if not ecosystem and is_pylock_manifest(filename):
                ecosystem = 'Python'
            if not ecosystem and _JULIA_VERSIONED_MANIFEST.fullmatch(filename):
                ecosystem = 'Julia'
            if not ecosystem and is_container_manifest(filename):
                ecosystem = 'Docker'
            if not ecosystem and path.suffix.lower() == '.gemspec':
                ecosystem = 'Ruby'
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
