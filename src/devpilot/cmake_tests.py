"""Opt-in CTest discovery for already-configured CMake build trees."""

from __future__ import annotations

from pathlib import Path
from typing import Any


# CMake's conventional build directory comes first, followed by common CLion
# build configurations and Visual Studio / CMakePresets output directories.
# Keep this list fixed rather than traversing arbitrary directories, where
# unexpected CTest configurations could run untrusted binaries.
_CTEST_BUILD_DIRS = (
    'build',
    'cmake-build-debug',
    'cmake-build-release',
    'cmake-build-relwithdebinfo',
    'cmake-build-minsizerel',
    'out/build',
    'out/build/default',
    'out/build/debug',
    'out/build/release',
    'out/build/x64-Debug',
    'out/build/x64-Release',
)


def _is_unlinked_build_tree(root: Path, directory: str) -> bool:
    """Require every component of a known build path to be a real directory.

    Checking only the final directory would follow an intermediate symlink
    such as out/build -> /another/project, exposing foreign CTest tests.
    """
    current = root
    for component in Path(directory).parts:
        current = current / component
        if current.is_symlink() or not current.is_dir():
            return False
    return True


def cmake_test_command(root: Path, names: set[str]) -> dict[str, Any] | None:
    """Preview CTest only when a regular, configured build tree exists.

    Do not run cmake or build project code during discovery. Restrict the
    target to known local build directories and ignore symlinked ancestors
    and markers. CTest may run arbitrary binaries and requires --yes.
    """
    if 'CMakeLists.txt' not in names:
        return None
    manifest = root / 'CMakeLists.txt'
    if manifest.is_symlink() or not manifest.is_file():
        return None
    for directory in _CTEST_BUILD_DIRS:
        if not _is_unlinked_build_tree(root, directory):
            continue
        ctest = root / directory / 'CTestTestfile.cmake'
        if ctest.is_symlink() or not ctest.is_file():
            continue
        return {
            'ecosystem': 'C/C++',
            'argv': ['ctest', '--test-dir', directory, '--output-on-failure', '--no-tests=error'],
            'reason': f'configured CMake {directory}/CTestTestfile.cmake',
        }
    return None
