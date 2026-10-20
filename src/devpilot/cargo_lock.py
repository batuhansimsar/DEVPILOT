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
_MAX_VERSION_LENGTH = 256
# Cargo.lock contains resolved versions, not Cargo.toml version requirements.
# Each package version must be SemVer with a full major.minor.patch triplet.
_SEMVER = re.compile(
    r'(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)'
    r'(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?'
    r'(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?\Z'
)


def _valid_version(version: object) -> bool:
    if not isinstance(version, str) or not 0 < len(version) <= _MAX_VERSION_LENGTH:
        return False
    if not _SEMVER.fullmatch(version):
        return False
    # Numeric prerelease identifiers must not have leading zeroes (SemVer 2.0).
    pre_release = version.split('+', 1)[0].partition('-')[2]
    return not any(
        len(part) > 1 and part.startswith('0') and part.isascii() and part.isdecimal()
        for part in pre_release.split('.') if part
    )



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
        # Every resolved Cargo.lock package has a version.  Do not turn
        # incomplete or corrupted records into seemingly valid dependencies.
        # Validate only the shape; never put version data into reports/errors.
        if not _valid_version(package.get('version')):
            raise ValueError('Cargo.lock packages must have valid version strings')
        names.add(name)
    return sorted(names)
