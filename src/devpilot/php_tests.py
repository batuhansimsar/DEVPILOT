"""Conservative, read-only PHPUnit discovery for Composer projects."""

from __future__ import annotations

from pathlib import Path
from typing import Any


_PHPUNIT_CONFIGS = ('phpunit.xml', 'phpunit.xml.dist')
_MAX_TEST_ENTRIES = 4096


def php_test_command(root: Path, names: set[str]) -> dict[str, Any] | None:
    """Detect configured PHPUnit or a conventional tests/ suite.

    Only inspect ordinary files; never follow symlinked manifests, config,
    or suite paths. Directory traversal is bounded and runs no project code.
    Test execution requires explicit CLI --yes consent.
    """
    manifest = root / 'composer.json'
    if 'composer.json' not in names or manifest.is_symlink() or not manifest.is_file():
        return None

    # When a config exists, PHPUnit reads the configured suite itself.
    # A linked config may point outside the selected project: do not trust it.
    present = [name for name in _PHPUNIT_CONFIGS if name in names]
    if any((root / name).is_symlink() or not (root / name).is_file() for name in present):
        return None
    if present:
        return {
            'ecosystem': 'PHP',
            'argv': ['php', 'vendor/bin/phpunit', '--configuration', present[0]],
            'reason': f'Composer project with {present[0]}',
        }

    tests = root / 'tests'
    if tests.is_symlink() or not tests.is_dir():
        return None
    pending = [tests]
    seen = 0
    try:
        while pending:
            for path in pending.pop().iterdir():
                seen += 1
                if seen > _MAX_TEST_ENTRIES:
                    return None
                if path.is_symlink():
                    continue
                if path.is_file() and path.name.endswith('Test.php'):
                    return {
                        'ecosystem': 'PHP',
                        'argv': ['php', 'vendor/bin/phpunit', 'tests'],
                        'reason': 'Composer project with conventional PHPUnit tests',
                    }
                if path.is_dir():
                    pending.append(path)
    except OSError:
        return None
    return None
