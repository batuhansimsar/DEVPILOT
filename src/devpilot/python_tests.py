"""Choose Python test runners matching the interpreter used for execution."""

from __future__ import annotations

import sys
from importlib.machinery import PathFinder
from pathlib import Path
from typing import Any


def python_test_command(root: Path) -> dict[str, Any] | None:
    """Discover an existing tests directory without executing project code.

    A pytest launcher on PATH may belong to a different virtual environment.
    Since DevPilot invokes sys.executable -m pytest, inspect that interpreter's
    import path instead of guessing from the external executable name.
    """
    tests = root / 'tests'
    if tests.is_symlink() or not tests.is_dir():
        return None
    if PathFinder.find_spec('pytest') is not None:
        return {'ecosystem': 'Python', 'argv': [sys.executable, '-m', 'pytest'],
                'reason': 'tests directory (pytest importable)'}
    return {'ecosystem': 'Python', 'argv': [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'],
            'reason': 'tests directory'}
