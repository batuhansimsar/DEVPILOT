"""Choose Python test runners matching the interpreter used for execution."""

from __future__ import annotations

import sys
from importlib.machinery import PathFinder
from pathlib import Path
from typing import Any


def _has_unittest_tests(tests: Path) -> bool:
    """Find a conventional unittest module without importing project code.

    ``unittest discover -s tests`` only descends into importable packages.
    Bound directory traversal and ignore symlinks to avoid trusting arbitrary
    linked paths during discovery. Unreadable or huge trees are inconclusive.
    """
    pending = [tests]
    entries_seen = 0
    while pending:
        directory = pending.pop()
        try:
            for entry in directory.iterdir():
                entries_seen += 1
                if entries_seen > 4096:
                    return False
                if entry.is_symlink():
                    continue
                if entry.is_file() and entry.name.startswith('test') and entry.name.endswith('.py'):
                    return True
                if entry.is_dir():
                    marker = entry / '__init__.py'
                    if not marker.is_symlink() and marker.is_file():
                        pending.append(entry)
        except OSError:
            return False
    return False


def python_test_command(root: Path) -> dict[str, Any] | None:
    """Discover a useful test command without executing project code.

    A pytest launcher on PATH may belong to a different virtual environment.
    Since DevPilot invokes sys.executable -m pytest, inspect that interpreter's
    import path instead of guessing from the external executable name.
    Without pytest, avoid reporting a successful zero-test unittest run.
    """
    tests = root / 'tests'
    if tests.is_symlink() or not tests.is_dir():
        return None
    if PathFinder.find_spec('pytest') is not None:
        return {'ecosystem': 'Python', 'argv': [sys.executable, '-m', 'pytest'],
                'reason': 'tests directory (pytest importable)'}
    if not _has_unittest_tests(tests):
        return None
    return {'ecosystem': 'Python', 'argv': [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'],
            'reason': 'tests directory'}
