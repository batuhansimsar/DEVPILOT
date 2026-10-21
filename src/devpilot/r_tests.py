"""Conservative testthat command discovery for R package projects."""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path
from typing import Any

from .r_manifests import is_r_manifest

_MAX_R_SUITE_ENTRIES = 4096
_MAX_DESCRIPTION_BYTES = 32768
_PACKAGE_NAME = re.compile(rb'[A-Za-z][A-Za-z0-9.]*\Z')


def _description_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    """Identify replacement or mutation of an untrusted DESCRIPTION file."""
    return (metadata.st_dev, metadata.st_ino, metadata.st_size,
            metadata.st_mtime_ns, metadata.st_ctime_ns)


def _valid_package_description(path: Path) -> bool:
    """Read a bounded, stable regular DESCRIPTION without following swapped links."""
    try:
        initial = path.lstat()
        if not stat.S_ISREG(initial.st_mode) or initial.st_size > _MAX_DESCRIPTION_BYTES:
            return False
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
        with os.fdopen(os.open(path, flags), 'rb') as source:
            opened = os.fstat(source.fileno())
            if (not stat.S_ISREG(opened.st_mode)
                    or opened.st_size > _MAX_DESCRIPTION_BYTES
                    or _description_identity(initial) != _description_identity(opened)):
                return False
            contents = source.read(_MAX_DESCRIPTION_BYTES + 1)
            if _description_identity(os.fstat(source.fileno())) != _description_identity(opened):
                return False
    except OSError:
        return False
    return len(contents) <= _MAX_DESCRIPTION_BYTES and any(
        _PACKAGE_NAME.fullmatch(line[len(b'Package:'):].strip())
        for line in contents.splitlines() if line.startswith(b'Package:')
    )




def _safe_test_tree(tests: Path, suite: Path) -> bool:
    """Inspect every test descendant before permitting testthat execution.

    testthat helpers and fixtures can live in nested directories. A single
    symlink anywhere beneath tests/ can escape the selected project; an
    unreadable or oversized tree is inconclusive and must fail closed.
    """
    pending = [tests]
    inspected = 0
    has_test = False
    try:
        while pending:
            directory = pending.pop()
            for candidate in directory.iterdir():
                inspected += 1
                if inspected > _MAX_R_SUITE_ENTRIES or candidate.is_symlink():
                    return False
                if candidate.is_dir():
                    pending.append(candidate)
                elif candidate.is_file():
                    # The standard testthat layout discovers test files at
                    # tests/testthat/, not arbitrary fixture subdirectories.
                    if (candidate.parent == suite
                            and candidate.name.startswith(('test-', 'test_'))
                            and candidate.suffix in ('.R', '.r')):
                        has_test = True
                else:
                    # Do not approve FIFOs, sockets or other special nodes.
                    return False
    except OSError:
        return False
    return has_test


def r_test_command(root: Path, names: set[str]) -> dict[str, Any] | None:
    """Discover package tests, without reading or executing project R code.

    A renv lockfile or RStudio marker alone is not evidence of runnable tests.
    Require an ordinary package DESCRIPTION, a conventional testthat entry
    point, and at least one real test file before suggesting test_local().
    The CLI executes this command only after explicit --yes approval.
    """
    if not any(
        is_r_manifest(name)
        and (root / name).is_file()
        and not (root / name).is_symlink()
        for name in names
    ):
        return None

    description = root / 'DESCRIPTION'
    tests = root / 'tests'
    entry = tests / 'testthat.R'
    suite = tests / 'testthat'
    if (not _valid_package_description(description)
            or tests.is_symlink() or not tests.is_dir()
            or entry.is_symlink() or not entry.is_file()
            or suite.is_symlink() or not suite.is_dir()
            or not _safe_test_tree(tests, suite)):
        return None


    return {
        'ecosystem': 'R',
        'argv': ['Rscript', '-e', 'testthat::test_local()'],
        'reason': 'R package with testthat entry point and tests',
    }
