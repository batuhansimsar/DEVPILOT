"""Choose Python test runners matching the interpreter used for execution."""

from __future__ import annotations

import sys
from importlib.machinery import PathFinder
from pathlib import Path
from typing import Any

_MAX_TEST_DISCOVERY_ENTRIES = 4096


def _has_unittest_tests(tests: Path) -> bool:
    """Find a conventional unittest module without importing project code.

    ``unittest discover -s tests`` only descends into importable packages.
    Bound directory traversal and reject symlinked modules or importable
    packages that unittest would otherwise execute outside the chosen tree.
    Unreadable or huge trees are inconclusive.
    """
    pending = [tests]
    entries_seen = 0
    found = False
    while pending:
        directory = pending.pop()
        try:
            for entry in directory.iterdir():
                entries_seen += 1
                if entries_seen > _MAX_TEST_DISCOVERY_ENTRIES:
                    return False
                if entry.is_symlink():
                    if ((entry.is_file() and entry.name.startswith('test') and entry.name.endswith('.py'))
                            or (entry.is_dir() and (entry / '__init__.py').is_file())):
                        return False
                    continue
                if entry.is_file() and entry.name.startswith('test') and entry.name.endswith('.py'):
                    found = True
                if entry.is_dir():
                    marker = entry / '__init__.py'
                    if marker.is_symlink():
                        return False
                    if marker.is_file():
                        pending.append(entry)
        except OSError:
            return False
    return found


def _pytest_suites_are_safe(root: Path) -> bool:
    """Do not propose pytest for linked or uninspectable conventional suites.

    Unlike unittest discovery, pytest walks test trees recursively, including
    symlinked files and directories. Scan both conventional suite names, since
    invoking pytest without explicit paths can collect either one. A bounded
    scan avoids unlimited work on untrusted project trees.
    """
    pending = []
    for name in ('tests', 'test'):
        suite = root / name
        if suite.is_symlink():
            return False
        if suite.is_dir():
            pending.append(suite)

    entries_seen = 0
    try:
        while pending:
            for entry in pending.pop().iterdir():
                entries_seen += 1
                if entries_seen > _MAX_TEST_DISCOVERY_ENTRIES or entry.is_symlink():
                    return False
                if entry.is_dir():
                    pending.append(entry)
    except OSError:
        return False
    return True


def python_test_command(root: Path) -> dict[str, Any] | None:
    """Discover a useful test command without executing project code.

    Prefer the conventional ``tests/`` folder, but recognize singular ``test/``
    folders with a discoverable Python test module too. If ``tests/`` contains
    no discoverable unittest tests, use ``test/`` as a fallback when pytest is
    unavailable. Avoid linked suite entries when selecting pytest, which may
    collect them even when they are not conventional unittest modules.

    A pytest launcher on PATH may belong to a different virtual environment.
    Since DevPilot invokes sys.executable -m pytest, inspect that interpreter's
    import path instead of guessing from the external executable name.
    Without pytest, avoid reporting a successful zero-test unittest run.
    """
    tests = root / 'tests'
    directory_name = 'tests'
    if tests.is_symlink():
        return None
    if not tests.is_dir():
        tests = root / 'test'
        directory_name = 'test'
        if tests.is_symlink() or not tests.is_dir() or not _has_unittest_tests(tests):
            return None
    if PathFinder.find_spec('pytest') is not None:
        if not _pytest_suites_are_safe(root):
            return None
        return {'ecosystem': 'Python', 'argv': [sys.executable, '-m', 'pytest'],
                'reason': f'{directory_name} directory (pytest importable)'}
    if not _has_unittest_tests(tests):
        if directory_name != 'tests':
            return None
        fallback = root / 'test'
        if fallback.is_symlink() or not fallback.is_dir() or not _has_unittest_tests(fallback):
            return None
        directory_name = 'test'
    return {'ecosystem': 'Python',
            'argv': [sys.executable, '-m', 'unittest', 'discover', '-s', directory_name],
            'reason': f'{directory_name} directory'}
