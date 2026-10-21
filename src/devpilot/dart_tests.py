"""Conservative Dart and Flutter test-command discovery."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


_MAX_PUBSPEC_BYTES = 128 * 1024
_DEPENDENCY_SECTION = re.compile(rb'(?:dependencies|dev_dependencies|dependency_overrides):[ \t]*(?:#.*)?\Z')
_DEPENDENCY_ENTRY = re.compile(
    rb'''(?:[A-Za-z][A-Za-z0-9_]*|'[A-Za-z][A-Za-z0-9_]*'|"[A-Za-z][A-Za-z0-9_]*"):[ \t]*(?:#.*)?\Z'''
)
_FLUTTER_SDK = re.compile(rb'''sdk:[ \t]*(?:flutter|'flutter'|"flutter")[ \t]*(?:#.*)?\Z''')


def _has_flutter_sdk_dependency(data: bytes) -> bool:
    """Recognize a Flutter SDK dependency, not unrelated YAML text.

    Examine only top-level dependency mappings and each package's direct
    sdk: flutter field. This deliberately avoids executing YAML tags or requiring
    a parser. Unknown YAML constructs default to Dart instead of guessing Flutter.
    """
    in_dependencies = False
    dependency_indent: int | None = None
    package_indent: int | None = None
    sdk_indent: int | None = None
    for line in data.removeprefix(b'\xef\xbb\xbf').splitlines():
        text = line.lstrip(b' ')
        if not text or text.startswith(b'#'):
            continue
        indent = len(line) - len(text)
        if indent == 0:
            in_dependencies = _DEPENDENCY_SECTION.fullmatch(text) is not None
            dependency_indent = package_indent = sdk_indent = None
            continue
        if not in_dependencies:
            continue
        if dependency_indent is None:
            dependency_indent = indent
        if indent == dependency_indent:
            package_indent = indent if _DEPENDENCY_ENTRY.fullmatch(text) else None
            sdk_indent = None
        elif package_indent is not None and indent > package_indent:
            if sdk_indent is None:
                sdk_indent = indent
            if indent == sdk_indent and _FLUTTER_SDK.fullmatch(text):
                return True
    return False


def dart_test_command(root: Path, names: set[str]) -> dict[str, Any] | None:
    """Return an opt-in test command only for an unlinked Dart project.

    Use Flutter's runner if pubspec.yaml declares an SDK Flutter dependency.
    Do not execute project code, follow linked markers, or read unbounded manifests.
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
    flutter = _has_flutter_sdk_dependency(data)
    return {
        'ecosystem': 'Dart',
        'argv': ['flutter', 'test'] if flutter else ['dart', 'test'],
        'reason': 'Flutter SDK dependency and test directory' if flutter
                  else 'pubspec.yaml with test directory',
    }
