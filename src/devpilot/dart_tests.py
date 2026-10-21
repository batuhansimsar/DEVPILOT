"""Discover a safe, explicitly opt-in Dart test command."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def dart_test_command(root: Path, names: set[str]) -> dict[str, Any] | None:
    """Suggest `dart test` for packages with an ordinary test directory.

    A lockfile alone is not a runnable project. Do not follow a symlinked
    pubspec or test directory; discovery never executes project scripts.
    """
    if 'pubspec.yaml' not in names:
        return None
    manifest = root / 'pubspec.yaml'
    tests = root / 'test'
    if (manifest.is_symlink() or not manifest.is_file()
            or tests.is_symlink() or not tests.is_dir()):
        return None
    return {'ecosystem': 'Dart', 'argv': ['dart', 'test'],
            'reason': 'pubspec.yaml with test directory'}
