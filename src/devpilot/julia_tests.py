"""Conservative test-command discovery for Julia package projects."""

from __future__ import annotations

from pathlib import Path
from typing import Any


_JULIA_PROJECT_FILES = frozenset({'Project.toml', 'JuliaProject.toml'})


def julia_test_command(root: Path, names: set[str]) -> dict[str, Any] | None:
    """Discover Julia's standard package tests without running project code.

    A Manifest.toml by itself does not define a package suitable for Pkg.test.
    Require a project manifest and a regular test/runtests.jl, and never follow
    a symlinked test directory or entry point during discovery.
    """
    if not names.intersection(_JULIA_PROJECT_FILES):
        return None
    test_dir = root / 'test'
    test_entry = test_dir / 'runtests.jl'
    if (test_dir.is_symlink() or not test_dir.is_dir()
            or test_entry.is_symlink() or not test_entry.is_file()):
        return None
    return {
        'ecosystem': 'Julia',
        'argv': ['julia', '--project=.', '-e', 'using Pkg; Pkg.test()'],
        'reason': 'Julia project with test/runtests.jl',
    }
