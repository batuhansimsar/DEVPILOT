"""Opt-in CTest discovery for already-configured CMake build trees."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def cmake_test_command(root: Path, names: set[str]) -> dict[str, Any] | None:
    """Preview CTest only when a regular, configured build tree exists.

    Do not run cmake or build project code during discovery. Restrict the
    target to the conventional build directory and ignore symlinked markers.
    CTest may run arbitrary project binaries and requires explicit --yes.
    """
    if 'CMakeLists.txt' not in names:
        return None
    manifest = root / 'CMakeLists.txt'
    build = root / 'build'
    ctest = build / 'CTestTestfile.cmake'
    if (manifest.is_symlink() or not manifest.is_file()
            or build.is_symlink() or not build.is_dir()
            or ctest.is_symlink() or not ctest.is_file()):
        return None
    return {
        'ecosystem': 'C/C++',
        'argv': ['ctest', '--test-dir', 'build', '--output-on-failure', '--no-tests=error'],
        'reason': 'configured CMake build/CTestTestfile.cmake',
    }
