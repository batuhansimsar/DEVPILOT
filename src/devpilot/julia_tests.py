"""Read-only discovery of Julia package test commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any


JULIA_PROJECT_FILES = ('Project.toml', 'JuliaProject.toml')


def julia_test_command(root: Path, names: set[str]) -> dict[str, Any] | None:
    """Plan Pkg.test only when a regular Julia project file is present.

    Julia's Manifest.toml files can identify a workspace but do not by
    themselves identify a testable package. Never open project files or
    follow symlinks during discovery. The CLI must require --yes before
    executing any project-supplied test code.
    """
    if not any(
        name in names and (root / name).is_file() and not (root / name).is_symlink()
        for name in JULIA_PROJECT_FILES
    ):
        return None
    return {
        'ecosystem': 'Julia',
        'argv': ['julia', '--project=.', '-e', 'using Pkg; Pkg.test()'],
        'reason': 'Julia project manifest (Pkg.test)',
    }
