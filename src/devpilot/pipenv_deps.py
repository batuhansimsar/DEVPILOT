"""Read-only inventory of packages recorded in a Pipenv lockfile."""

from __future__ import annotations

import json
import math
import re

_PACKAGE_NAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?\Z")
_SEPARATOR = re.compile(r"[-_.]+")


def _reject_nonfinite(_value: str) -> None:
    raise ValueError("Pipfile.lock must use finite JSON numbers")


def _parse_finite_float(value: str) -> float:
    """Reject JSON exponents that overflow a Python float to infinity."""
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Pipfile.lock must use finite JSON numbers")
    return number


def _unique_object_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Fail closed on ambiguous JSON without exposing keys or values in errors."""
    entries: dict[str, object] = {}
    for key, value in pairs:
        if key in entries:
            raise ValueError("Pipfile.lock contains duplicate object keys")
        entries[key] = value
    return entries


def parse_pipfile_lock(content: str) -> dict[str, list[str]]:
    """List locked default and development package names, never their values.

    Lockfiles may contain authenticated indexes, URLs and hashes, so neither
    source metadata nor per-package values should reach diagnostic reports.
    """
    lock = json.loads(content, parse_constant=_reject_nonfinite,
                      parse_float=_parse_finite_float,
                      object_pairs_hook=_unique_object_keys)
    if not isinstance(lock, dict):
        raise ValueError("Pipfile.lock root must be an object")

    groups: dict[str, list[str]] = {}
    for group in ("default", "develop"):
        entries = lock.get(group, {})
        if not isinstance(entries, dict):
            raise ValueError(f"Pipfile.lock {group} must be an object")
        if not all(isinstance(value, dict) for value in entries.values()):
            raise ValueError(f"Pipfile.lock {group} packages must be objects")
        # Never omit an invalid key: a partial dependency inventory is misleading.
        # The message must not reflect potentially secret-containing lockfile keys.
        if any(not _PACKAGE_NAME.fullmatch(name) for name in entries):
            raise ValueError(f"Pipfile.lock {group} contains invalid package names")
        normalized: set[str] = set()
        for raw_name in entries:
            name = _SEPARATOR.sub("-", raw_name).lower()
            if name in normalized:
                # Pip treats these spellings as one package. Silently merging
                # them would conceal conflicting entries in the lockfile.
                raise ValueError(f"Pipfile.lock {group} contains duplicate normalized package names")
            normalized.add(name)
        if normalized:
            groups[group] = sorted(normalized)
    return groups
