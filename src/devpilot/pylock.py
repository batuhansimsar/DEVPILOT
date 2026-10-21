"""Privacy-safe PEP 751 lockfile inventory (names only, never credentials)."""

from __future__ import annotations

import re

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

_PACKAGE_NAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?\Z")
_SEPARATOR = re.compile(r"[-_.]+")
# Only one nonempty, ASCII filename-safe variant is allowed. The former
# [^.]+ variant also matched slashes, whitespace and terminal controls, which
# could incorrectly identify unrelated files as standardized lockfiles.
_PYLOCK_FILE = re.compile(r"pylock(?:\.[A-Za-z0-9][A-Za-z0-9_-]*)?\.toml\Z")


# Bound direct calls as well as scans through the size-limited manifest reader.
MAX_PYLOCK_INPUT_CHARS = 2 * 1024 * 1024
MAX_PYLOCK_PACKAGES = 100_000


def is_pylock_manifest(filename: str) -> bool:
    """Accept pylock.toml and safe pylock.<name>.toml variants."""
    return isinstance(filename, str) and _PYLOCK_FILE.fullmatch(filename) is not None


def parse_pylock(content: str) -> list[str]:
    """Read valid locked package names, rejecting malformed files privately."""
    if not isinstance(content, str) or len(content) > MAX_PYLOCK_INPUT_CHARS:
        raise ValueError('pylock.toml input exceeds safe size limit or is invalid')
    try:
        data = tomllib.loads(content.removeprefix('\ufeff'))
    except (tomllib.TOMLDecodeError, RecursionError, ValueError, OverflowError):
        raise ValueError('invalid pylock.toml TOML') from None
    if data.get('lock-version') != '1.0':
        raise ValueError('unsupported pylock.toml lock-version')
    if not isinstance(data.get('created-by'), str) or not data['created-by'].strip():
        raise ValueError('pylock.toml missing created-by')
    packages = data.get('packages')
    if not isinstance(packages, list) or len(packages) > MAX_PYLOCK_PACKAGES:
        raise ValueError('pylock.toml packages must be a bounded array')
    names: set[str] = set()
    for package in packages:
        if not isinstance(package, dict):
            raise ValueError('pylock.toml packages must be tables with valid names')
        name = package.get('name')
        if (not isinstance(name, str) or len(name) > 214
                or not _PACKAGE_NAME.fullmatch(name)):
            raise ValueError('pylock.toml packages must be tables with valid names')
        names.add(_SEPARATOR.sub('-', name).lower())
    return sorted(names)
