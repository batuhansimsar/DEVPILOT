"""Read-only, privacy-safe dependency inventory for Pipenv Pipfiles.

Only declared package names are returned. Sources, versions, hashes, editable
paths, and VCS URLs are never copied into reports or error messages.
"""

from __future__ import annotations

import re

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

_PACKAGE_NAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?\Z")
_SEPARATORS = re.compile(r"[-_.]+")
_MAX_PACKAGE_NAME_LENGTH = 214


def parse_pipfile_dependencies(content: str) -> dict[str, list[str]]:
    """List normalized package names from Pipfile packages and dev-packages.

    Reject malformed or duplicate declarations rather than silently producing
    an incomplete or ambiguous inventory. Diagnostics never include untrusted
    package names, credentials, or dependency specifiers.
    """
    try:
        manifest = tomllib.loads(content.removeprefix("\ufeff"))
    except tomllib.TOMLDecodeError:
        raise ValueError("invalid Pipfile TOML") from None

    result: dict[str, list[str]] = {}
    for group in ("packages", "dev-packages"):
        entries = manifest.get(group, {})
        if not isinstance(entries, dict):
            raise ValueError(f"Pipfile {group} must be a table")
        names: set[str] = set()
        for name, spec in entries.items():
            if (len(name) > _MAX_PACKAGE_NAME_LENGTH
                    or not _PACKAGE_NAME.fullmatch(name)):
                raise ValueError(f"Pipfile {group} contains an invalid package name")
            # Pipenv supports both a version string and an inline/table spec
            # (e.g. {git = "...", ref = "..."}). Other shapes are invalid.
            if not isinstance(spec, (str, dict)):
                raise ValueError(f"Pipfile {group} contains an invalid package specification")
            canonical = _SEPARATORS.sub("-", name).lower()
            if canonical in names:
                raise ValueError(f"Pipfile {group} contains duplicate normalized package names")
            names.add(canonical)
        if names:
            result[group] = sorted(names)
    return result
