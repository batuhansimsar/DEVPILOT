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
                    return False
                if (
                    entry.is_file()
                    and entry.name.startswith('test')
                    and entry.name.endswith('.py')
                    and entry.stem.isidentifier()
                ):
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



def _root_test_modules(root: Path) -> tuple[bool, bool]:
    """Find root-level unittest/pytest files without following links.

    Reject inconclusive, unreadable, or exceptionally large root listings.
    Pytest also recognizes *_test.py, but unittest's default glob does not.
    """
    has_unittest = False
    has_pytest = False
    try:
        for count, entry in enumerate(root.iterdir(), 1):
            if count > 4096:
                return False, False
            if entry.is_symlink() or not entry.is_file():
                continue
            name = entry.name
            if name.startswith('test') and name.endswith('.py'):
                has_unittest = True
            if (name.startswith('test_') or name.endswith('_test.py')) and name.endswith('.py'):
                has_pytest = True
    except OSError:
        return False, False
    return has_unittest, has_pytest


def python_test_command(root: Path) -> dict[str, Any] | None:
    """Discover a useful test command without executing project code.

    Prefer conventional tests/ or test/ folders. When neither supplies
    discoverable unittest modules, recognize root-level Python test files.
    Never follow linked markers; only offer commands runnable by the chosen
    interpreter. Without pytest, use unittest's own test*.py discovery glob.
    """
    tests = root / 'tests'
    directory_name = 'tests'
    if tests.is_symlink():
        return None
    if not tests.is_dir():
        tests = root / 'test'
        directory_name = 'test'
        if tests.is_symlink():
            return None
        if not tests.is_dir() or not _has_unittest_tests(tests):
            tests = None
    if tests is not None and PathFinder.find_spec('pytest') is not None:
        if not _pytest_suites_are_safe(root):
            return None
        return {'ecosystem': 'Python', 'argv': [sys.executable, '-m', 'pytest'],
                'reason': f'{directory_name} directory (pytest importable)'}
    if tests is not None and not _has_unittest_tests(tests):
        fallback = root / 'test'
        if directory_name != 'tests' or fallback.is_symlink():
            tests = None
        elif fallback.is_dir() and _has_unittest_tests(fallback):
            tests, directory_name = fallback, 'test'
        else:
            tests = None
    if tests is not None:
        return {'ecosystem': 'Python',
                'argv': [sys.executable, '-m', 'unittest', 'discover', '-s', directory_name],
                'reason': f'{directory_name} directory'}

    # A linked test directory would be traversed by pytest at execution time.
    if (root / 'test').is_symlink():
        return None
    has_unittest, has_pytest = _root_test_modules(root)
    if has_pytest and PathFinder.find_spec('pytest') is not None:
        if not _pytest_suites_are_safe(root):
            return None
        return {'ecosystem': 'Python', 'argv': [sys.executable, '-m', 'pytest'],
                'reason': 'root-level pytest test files'}
    if has_unittest:
        return {'ecosystem': 'Python',
                'argv': [sys.executable, '-m', 'unittest', 'discover', '-s', '.'],
                'reason': 'root-level unittest test files'}
    return None
