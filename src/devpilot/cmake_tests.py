"""Opt-in CTest discovery for already-configured CMake build trees."""

from __future__ import annotations

from pathlib import Path
from typing import Any


# CMake's conventional build directory comes first, followed by the default
# CLion build directories. Keep this fixed rather than inspecting arbitrary
# directories (which might contain untrusted CTest configuration).
_CTEST_BUILD_DIRS = ('build', 'cmake-build-debug', 'cmake-build-release')


def cmake_test_command(root: Path, names: set[str]) -> dict[str, Any] | None:
    """Preview CTest only when a regular, configured build tree exists.

    Do not run cmake or build project code during discovery. Restrict the
    target to known local build directories and ignore symlinked markers.
    CTest may run arbitrary project binaries and requires explicit --yes.
    """
    if 'CMakeLists.txt' not in names:
        return None
    manifest = root / 'CMakeLists.txt'
    if manifest.is_symlink() or not manifest.is_file():
        return None
    for directory in _CTEST_BUILD_DIRS:
        build = root / directory
        ctest = build / 'CTestTestfile.cmake'
        if (build.is_symlink() or not build.is_dir()
                or ctest.is_symlink() or not ctest.is_file()):
            continue
        return {
            'ecosystem': 'C/C++',
            'argv': ['ctest', '--test-dir', directory, '--output-on-failure', '--no-tests=error'],
            'reason': f'configured CMake {directory}/CTestTestfile.cmake',
        }
    return None
