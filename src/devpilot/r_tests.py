"""Conservative testthat command discovery for R/RStudio projects."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .r_manifests import is_r_manifest


def r_test_command(root: Path, names: set[str]) -> dict[str, Any] | None:
    """Discover conventional testthat suites without executing any R code.

    An R project marker alone never implies runnable tests. Reject linked test
    directories and linked entry points so discovery stays within the project.
    The caller requires explicit --yes consent before running the command.
    """
    if not any(is_r_manifest(name) and (root / name).is_file()
               and not (root / name).is_symlink() for name in names):
        return None

    tests = root / 'tests'
    suite = tests / 'testthat'
    if (tests.is_symlink() or not tests.is_dir()
            or suite.is_symlink() or not suite.is_dir()):
        return None

    try:
        has_tests = any(
            path.name.startswith('test-') and path.name.endswith('.R')
            and path.is_file() and not path.is_symlink()
            for path in suite.iterdir()
        )
    except OSError:
        return None
    if not has_tests:
        return None

    description = root / 'DESCRIPTION'
    if description.is_file() and not description.is_symlink():
        # test_local loads package code and mirrors normal package development.
        expression = 'testthat::test_local(".")'
    else:
        # RStudio/renv projects may contain testthat tests without a package.
        expression = 'testthat::test_dir("tests/testthat")'
    return {
        'ecosystem': 'R',
        'argv': ['Rscript', '-e', expression],
        'reason': 'R project with tests/testthat/test-*.R',
    }
