"""Conservative testthat command discovery for R package projects."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .r_manifests import is_r_manifest

_MAX_DESCRIPTION_BYTES = 32768
_PACKAGE_NAME = re.compile(rb'[A-Za-z][A-Za-z0-9.]*\Z')


def _valid_package_description(path: Path) -> bool:
    """Reject generic, linked and oversized DESCRIPTION files as package evidence."""
    if path.is_symlink() or not path.is_file():
        return False
    try:
        with path.open('rb') as source:
            contents = source.read(_MAX_DESCRIPTION_BYTES + 1)
    except OSError:
        return False
    return len(contents) <= _MAX_DESCRIPTION_BYTES and any(
        _PACKAGE_NAME.fullmatch(line[len(b'Package:'):].strip())
        for line in contents.splitlines() if line.startswith(b'Package:')
    )




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
            or suite.is_symlink() or not suite.is_dir()):
        return None

    try:
        # testthat can execute every matching test file, not just the first
        # regular one. Reject a suite containing any linked test entry point.
        candidates = list(suite.glob('test-*.R'))
        if any(test.is_symlink() for test in candidates):
            return None
        if not any(test.is_file() for test in candidates):
            return None
    except OSError:
        return None

    return {
        'ecosystem': 'R',
        'argv': ['Rscript', '-e', 'testthat::test_local()'],
        'reason': 'R package with testthat entry point and tests',
    }
