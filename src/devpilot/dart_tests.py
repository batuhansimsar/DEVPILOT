"""Conservative Dart and Flutter test-command discovery."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


_MAX_PUBSPEC_BYTES = 128 * 1024
_FLUTTER_SDK = re.compile(rb'(?m)^[ \t]*sdk:[ \t]*flutter[ \t]*(?:#.*)?$')


def dart_test_command(root: Path, names: set[str]) -> dict[str, Any] | None:
    """Return an opt-in test command only for an unlinked Dart project.

    Use Flutter's runner if pubspec.yaml declares sdk: flutter. Do not
    execute project code, follow linked markers, or read unbounded manifests.
    """
    if 'pubspec.yaml' not in names:
        return None
    manifest = root / 'pubspec.yaml'
    tests = root / 'test'
    if (manifest.is_symlink() or not manifest.is_file()
            or tests.is_symlink() or not tests.is_dir()):
        return None
    try:
        with manifest.open('rb') as stream:
            data = stream.read(_MAX_PUBSPEC_BYTES + 1)
    except OSError:
        return None
    if len(data) > _MAX_PUBSPEC_BYTES:
        return None
    flutter = bool(_FLUTTER_SDK.search(data))
    return {
        'ecosystem': 'Dart',
        'argv': ['flutter', 'test'] if flutter else ['dart', 'test'],
        'reason': 'Flutter SDK dependency and test directory' if flutter
                  else 'pubspec.yaml with test directory',
    }
