"""Conservative test-command discovery for Julia package projects."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


_JULIA_PROJECT_FILES = frozenset({'Project.toml', 'JuliaProject.toml'})
_JULIA_MANIFEST_FILES = frozenset({'Manifest.toml', 'JuliaManifest.toml'})
_VERSIONED_JULIA_MANIFEST = re.compile(r'Manifest-v[0-9]+\.[0-9]+\.toml\Z')
_MAX_TEST_TREE_ENTRIES = 4096


def _safe_package_manifests(root: Path, names: set[str]) -> bool:
    """Avoid loading package lockfiles through links or special filesystem nodes.

    Julia's Pkg can use a version-specific Manifest-vX.Y.toml in preference
    to Manifest.toml. Check those advertised by the root scan as well as both
    conventional manifest names, including dangling symlinks.
    """
    candidates = _JULIA_MANIFEST_FILES | {
        name for name in names if _VERSIONED_JULIA_MANIFEST.fullmatch(name)
    }
    for name in candidates:
        manifest = root / name
        if manifest.is_symlink() or (manifest.exists() and not manifest.is_file()):
            return False
    return True


def _safe_test_tree(test_dir: Path) -> bool:
    """Fail closed on linked, unreadable, or excessively large Julia test trees.

    Pkg.test() may read helpers and test-specific manifests in addition to
    runtests.jl, so checking only the entry point cannot contain linked files.
    """
    pending = [test_dir]
    inspected = 0
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    inspected += 1
                    if inspected > _MAX_TEST_TREE_ENTRIES or entry.is_symlink():
                        return False
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(Path(entry.path))
        except OSError:
            return False
    return True


def julia_test_command(root: Path, names: set[str]) -> dict[str, Any] | None:
    """Discover Julia's standard package tests without running project code.

    A Manifest.toml by itself does not define a package suitable for Pkg.test.
    Require a project manifest and a regular test/runtests.jl, and never follow
    a symlinked project manifest, lockfile, or anything in the test tree.
    """
    project_files = names.intersection(_JULIA_PROJECT_FILES)
    # Julia prefers Project.toml over JuliaProject.toml. Root filename scans
    # can omit symlinks, so inspect *both* candidates even when not advertised;
    # otherwise an unlisted linked Project.toml could be loaded by Pkg.test().
    if any(
        (root / name).is_symlink() or
        ((root / name).exists() and not (root / name).is_file())
        for name in _JULIA_PROJECT_FILES
    ):
        return None
    if (not project_files or any(not (root / name).is_file() for name in project_files)
            or not _safe_package_manifests(root, names)):
        return None
    test_dir = root / 'test'
    test_entry = test_dir / 'runtests.jl'
    if (test_dir.is_symlink() or not test_dir.is_dir()
            or test_entry.is_symlink() or not test_entry.is_file()
            or not _safe_test_tree(test_dir)):
        return None
    return {
        'ecosystem': 'Julia',
        'argv': ['julia', '--project=.', '-e', 'using Pkg; Pkg.test()'],
        'reason': 'Julia project with test/runtests.jl',
    }
