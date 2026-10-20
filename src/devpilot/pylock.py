"""Privacy-safe PEP 751 lockfile inventory (names only, never credentials)."""

from __future__ import annotations

import re

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

_PACKAGE_NAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?\Z")
_SEPARATOR = re.compile(r"[-_.]+")
_PYLOCK_FILE = re.compile(r"pylock(?:\.[^.]+)?\.toml\Z")


def is_pylock_manifest(filename: str) -> bool:
    """Accept pylock.toml and standardized pylock.<name>.toml variants."""
    return _PYLOCK_FILE.fullmatch(filename) is not None


def parse_pylock(content: str) -> list[str]:
    """Read valid locked package names, rejecting malformed files privately."""
    try:
        data = tomllib.loads(content.removeprefix('\ufeff'))
    except (tomllib.TOMLDecodeError, RecursionError, ValueError, OverflowError):
        raise ValueError('invalid pylock.toml TOML') from None
    if data.get('lock-version') != '1.0':
        raise ValueError('unsupported pylock.toml lock-version')
    if not isinstance(data.get('created-by'), str) or not data['created-by'].strip():
        raise ValueError('pylock.toml missing created-by')
    packages = data.get('packages')
    if not isinstance(packages, list):
        raise ValueError('pylock.toml packages must be an array')
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
