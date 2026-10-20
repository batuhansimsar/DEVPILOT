"""Read-only package-name inventory for uv.lock files.

Only the normalized names of locked packages are returned. Versions, indexes,
source URLs, hashes, and other metadata are deliberately ignored.
"""

from __future__ import annotations

import re

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

_PACKAGE_NAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?\Z")
_SEPARATOR = re.compile(r"[-_.]+")
_MAX_PACKAGE_NAME_LENGTH = 214


def parse_uv_lock(content: str) -> list[str]:
    """Return sorted, unique, canonical package names from a uv lockfile.

    Fail closed for malformed package records: silently ignoring records would
    make the reported dependency inventory misleading. Never reflect the
    original TOML or an untrusted package name into exception messages.
    """
    try:
        # The scanner reads UTF-8-SIG, but direct library callers may hand us
        # decoded text that still includes a UTF-8 byte-order mark.
        document = tomllib.loads(content.removeprefix('\ufeff'))
    except tomllib.TOMLDecodeError:
        raise ValueError("invalid uv.lock TOML") from None

    packages = document.get("package", [])
    if not isinstance(packages, list):
        raise ValueError("uv.lock package entries must be an array")

    names: set[str] = set()
    for package in packages:
        if not isinstance(package, dict):
            raise ValueError("uv.lock packages must be tables with valid names")
        name = package.get("name")
        if (not isinstance(name, str) or len(name) > _MAX_PACKAGE_NAME_LENGTH
                or not _PACKAGE_NAME.fullmatch(name)):
            raise ValueError("uv.lock packages must be tables with valid names")
        names.add(_SEPARATOR.sub("-", name).lower())
    return sorted(names)
