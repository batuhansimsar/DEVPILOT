"""Conservative Dart and Flutter test-command discovery."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


_MAX_PUBSPEC_BYTES = 128 * 1024
_MAX_TEST_ENTRIES = 10000
# YAML mapping keys may be plain or quoted. Limit detection to conventional
# pubspec dependency sections and package identifiers, not arbitrary YAML keys.
_DEPENDENCY_SECTION = re.compile(
    rb'''(?:dependencies|dev_dependencies|dependency_overrides|"(?:dependencies|dev_dependencies|dependency_overrides)"|'(?:dependencies|dev_dependencies|dependency_overrides)')[ \t]*:[ \t]*(?:#.*)?\Z'''
)
_DEPENDENCY_ENTRY = re.compile(
    rb'''(?:[A-Za-z][A-Za-z0-9_]*|'[A-Za-z][A-Za-z0-9_]*'|"[A-Za-z][A-Za-z0-9_]*")[ \t]*:[ \t]*(?:#.*)?\Z'''
)
_FLUTTER_SDK = re.compile(rb'''(?:sdk|"sdk"|'sdk')[ \t]*:[ \t]*(?:flutter|'flutter'|"flutter")[ \t]*(?:#.*)?\Z''')

_INLINE_FLUTTER_SDK = re.compile(
    rb'''(?:[A-Za-z][A-Za-z0-9_]*|'[A-Za-z][A-Za-z0-9_]*'|"[A-Za-z][A-Za-z0-9_]*")[ \t]*:[ \t]*\{[ \t]*(?:sdk|"sdk"|'sdk')[ \t]*:[ \t]*(?:flutter|"flutter"|'flutter')[ \t]*\}[ \t]*(?:#.*)?\Z'''
)

def _has_flutter_sdk_dependency(data: bytes) -> bool:
    """Recognize Flutter SDK dependencies in block or simple inline YAML mappings.

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
            if _INLINE_FLUTTER_SDK.fullmatch(text):
                return True
            package_indent = indent if _DEPENDENCY_ENTRY.fullmatch(text) else None
            sdk_indent = None
        elif package_indent is not None and indent > package_indent:
            if sdk_indent is None:
                sdk_indent = indent
            if indent == sdk_indent and _FLUTTER_SDK.fullmatch(text):
                return True
    return False


def _safe_test_tree(tests: Path) -> bool:
    """Reject linked or unreadable test descendants with bounded traversal.

    The Dart/Flutter test runner discovers tests recursively. Linked entries
    can unexpectedly run files outside the selected project.
    """
    pending = [tests]
    inspected = 0
    while pending:
        folder = pending.pop()
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    inspected += 1
                    if inspected > _MAX_TEST_ENTRIES or entry.is_symlink():
                        return False
                    if entry.is_dir(follow_symlinks=False):
                        pending.append(Path(entry.path))
        except OSError:
            return False
    return True


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
            or tests.is_symlink() or not tests.is_dir()
            or not _safe_test_tree(tests)):
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
