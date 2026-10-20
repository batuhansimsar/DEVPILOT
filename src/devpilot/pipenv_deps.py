"""Read-only inventory of packages recorded in a Pipenv lockfile."""

from __future__ import annotations

import json
import re

_PACKAGE_NAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?\Z")
_SEPARATOR = re.compile(r"[-_.]+")


def _reject_nonfinite(_value: str) -> None:
    raise ValueError("Pipfile.lock must use finite JSON numbers")


def parse_pipfile_lock(content: str) -> dict[str, list[str]]:
    """List locked default and development package names, never their values.

    Lockfiles may contain authenticated indexes, URLs and hashes, so neither
    source metadata nor per-package values should reach diagnostic reports.
    """
    lock = json.loads(content, parse_constant=_reject_nonfinite)
    if not isinstance(lock, dict):
        raise ValueError("Pipfile.lock root must be an object")

    groups: dict[str, list[str]] = {}
    for group in ("default", "develop"):
        entries = lock.get(group, {})
        if not isinstance(entries, dict):
            raise ValueError(f"Pipfile.lock {group} must be an object")
        if not all(isinstance(value, dict) for value in entries.values()):
            raise ValueError(f"Pipfile.lock {group} packages must be objects")
        names = sorted({
            _SEPARATOR.sub("-", name).lower()
            for name in entries if _PACKAGE_NAME.fullmatch(name)
        })
        if names:
            groups[group] = names
    return groups
