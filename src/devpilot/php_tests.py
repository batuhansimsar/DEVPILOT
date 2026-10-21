"""Conservative, read-only PHPUnit and Pest discovery for Composer projects."""

from __future__ import annotations

from pathlib import Path
from typing import Any


_PHPUNIT_CONFIGS = ('phpunit.xml', 'phpunit.xml.dist')
_MAX_TEST_ENTRIES = 4096


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
    pest_marker = tests / 'Pest.php'
    uses_pest = (not tests.is_symlink() and tests.is_dir()
                 and not pest_marker.is_symlink() and pest_marker.is_file())
    runner = 'vendor/bin/pest' if uses_pest else 'vendor/bin/phpunit'
    if present:
        return {
            'ecosystem': 'PHP',
            'argv': ['php', runner, '--configuration', present[0]],
            'reason': f'Composer project with {present[0]}' + (' (Pest)' if uses_pest else ''),
        }

    if tests.is_symlink() or not tests.is_dir():
        return None
    pending = [tests]
    seen = 0
    has_tests = False
    try:
        while pending:
            for path in pending.pop().iterdir():
                seen += 1
                if seen > _MAX_TEST_ENTRIES or path.is_symlink():
                    # Both test runners can recursively discover linked files.
                    # Fail closed even if an ordinary test was already found.
                    return None
                if path.is_file() and path.name.endswith('Test.php'):
                    has_tests = True
                elif path.is_dir():
                    pending.append(path)
    except OSError:
        return None
    if not has_tests:
        return None
    return {
        'ecosystem': 'PHP',
        'argv': ['php', runner, 'tests'],
        'reason': 'Composer project with conventional '
                  + ('Pest' if uses_pest else 'PHPUnit') + ' tests',
    }
