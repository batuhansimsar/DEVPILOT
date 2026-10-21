"""Conservative, read-only PHPUnit and Pest discovery for Composer projects."""

from __future__ import annotations

from pathlib import Path
from typing import Any


_PHPUNIT_CONFIGS = ('phpunit.xml', 'phpunit.xml.dist')
_MAX_TEST_ENTRIES = 4096


def _inspect_php_test_tree(tests: Path) -> tuple[bool, bool]:
    """Check every conventional suite descendant without following links.

    Configured PHPUnit/Pest runs can load a tests/ tree without relying on a
    filename discovery marker, so inspect even when no *Test.php files exist.
    """
    pending = [tests]
    seen = 0
    has_tests = False
    try:
        while pending:
            for path in pending.pop().iterdir():
                seen += 1
                if seen > _MAX_TEST_ENTRIES or path.is_symlink():
                    # Both runners can recursively discover linked files.
                    return False, False
                if path.is_file() and path.name.endswith('Test.php'):
                    has_tests = True
                elif path.is_dir():
                    pending.append(path)
    except OSError:
        return False, False
    return True, has_tests


def php_test_command(root: Path, names: set[str]) -> dict[str, Any] | None:
    """Detect configured PHPUnit/Pest or a conventional tests/ suite.

    A regular tests/Pest.php selects the Pest launcher rather than PHPUnit.
    Only inspect ordinary files; never follow symlinked manifests, config,
    suite paths or Pest markers. Traversal is bounded and runs no project code.
    Test execution requires explicit CLI --yes consent.
    """
    manifest = root / 'composer.json'
    if 'composer.json' not in names or manifest.is_symlink() or not manifest.is_file():
        return None

    # When a config exists, the selected runner reads the configured suite.
    # A linked config may point outside the selected project: do not trust it.
    present = [name for name in _PHPUNIT_CONFIGS if name in names]
    if any((root / name).is_symlink() or not (root / name).is_file() for name in present):
        return None

    tests = root / 'tests'
    if tests.is_symlink():
        return None
    # A configured suite need not have a conventional tests/ directory, but
    # it must not conceal unsafe descendants when that directory is present.
    if tests.is_dir():
        safe, has_tests = _inspect_php_test_tree(tests)
        if not safe:
            return None
    else:
        has_tests = False
    pest_marker = tests / 'Pest.php'
    uses_pest = (tests.is_dir()
                 and not pest_marker.is_symlink() and pest_marker.is_file())
    runner = 'vendor/bin/pest' if uses_pest else 'vendor/bin/phpunit'
    if present:
        return {
            'ecosystem': 'PHP',
            'argv': ['php', runner, '--configuration', present[0]],
            'reason': f'Composer project with {present[0]}' + (' (Pest)' if uses_pest else ''),
        }

    if not tests.is_dir() or not has_tests:
        return None
    return {
        'ecosystem': 'PHP',
        'argv': ['php', runner, 'tests'],
        'reason': 'Composer project with conventional '
                  + ('Pest' if uses_pest else 'PHPUnit') + ' tests',
    }
