"""Privacy-safe inventory of locked package names from Poetry lockfiles.

Poetry's lock formats use TOML [[package]] records. This parser never
returns versions, hashes, source URLs or other package metadata.
"""

from __future__ import annotations

import re

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

_PACKAGE_NAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?\Z")
_SEPARATOR = re.compile(r"[-_.]+")
# Enforce the dependency scanner's 512 KB budget for direct parser calls too.
# Check encoded bytes: a short Unicode string can exceed the file-size limit.
MAX_POETRY_LOCK_INPUT_BYTES = 512_000


def parse_poetry_lock(content: str) -> list[str]:
    """Return sorted, unique normalized names for every locked package.

    Invalid or ambiguous records fail closed rather than yielding a misleading
    partial inventory. Errors must not echo raw TOML or untrusted package names.
    """
    if not isinstance(content, str) or len(content) > MAX_POETRY_LOCK_INPUT_BYTES:
        raise ValueError("poetry.lock input exceeds safe size limit or is invalid")
    try:
        encoded_length = len(content.encode('utf-8'))
    except UnicodeError:
        raise ValueError("poetry.lock input must contain valid Unicode") from None
    if encoded_length > MAX_POETRY_LOCK_INPUT_BYTES:
        raise ValueError("poetry.lock input exceeds safe size limit or is invalid")
    try:
        # Direct callers may supply text decoded with UTF-8 rather than
        # UTF-8-SIG. Match the scanner and the uv.lock parser by ignoring
        # exactly one leading byte-order mark, never BOMs inside the file.
        document = tomllib.loads(content.removeprefix('\ufeff'))
    except (ValueError, RecursionError, OverflowError):
        # TOML metadata can exceed numeric or nesting limits. Suppress parser
        # details to avoid exposing private lockfile contents.
        raise ValueError("invalid poetry.lock TOML") from None

    packages = document.get("package", [])
    if not isinstance(packages, list):
        raise ValueError("poetry.lock package entries must be an array")

    names: set[str] = set()
    for package in packages:
        if not isinstance(package, dict):
            raise ValueError("poetry.lock packages must be tables with valid names")
        name = package.get("name")
        if (not isinstance(name, str) or len(name) > 214
                or not _PACKAGE_NAME.fullmatch(name)):
            raise ValueError("poetry.lock packages must be tables with valid names")
        names.add(_SEPARATOR.sub("-", name).lower())
    return sorted(names)
