"""Privacy-safe inventory of locked Rust crates from Cargo.lock.

Only package names are returned; never versions, checksums or registry URLs.
"""

from __future__ import annotations

import re

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

_CRATE_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_-]*\Z")
_MAX_CRATE_NAME_LENGTH = 214


def parse_cargo_lock(content: str) -> list[str]:
    """Return unique, sorted crate names from Cargo.lock package tables.

    Reject malformed lockfiles and invalid package records rather than
    returning a partial inventory. Errors must never expose private sources.
    """
    try:
        document = tomllib.loads(content.removeprefix('\ufeff'))
    except (tomllib.TOMLDecodeError, RecursionError):
        raise ValueError('invalid Cargo.lock TOML') from None

    packages = document.get('package', [])
    if not isinstance(packages, list):
        raise ValueError('Cargo.lock package entries must be an array')

    names: set[str] = set()
    for package in packages:
        if not isinstance(package, dict):
            raise ValueError('Cargo.lock packages must be tables with valid names')
        name = package.get('name')
        if (not isinstance(name, str) or len(name) > _MAX_CRATE_NAME_LENGTH
                or not _CRATE_NAME.fullmatch(name)):
            raise ValueError('Cargo.lock packages must be tables with valid names')
        names.add(name)
    return sorted(names)
