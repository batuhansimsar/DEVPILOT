"""Read-only Composer lockfile inventory without exposing dependency metadata.

Only validated, canonical package names are retained. Versions, distribution
URLs, source URLs, credentials, and hashes must not be included in reports.
"""

from __future__ import annotations

import json

from .composer_deps import _PACKAGE_NAME, _reject_nonfinite_number, _unique_object_keys
from .json_numbers import parse_finite_json_float
from .json_nesting import validate_json_nesting

_MAX_NAME_LENGTH = 214


def parse_composer_lock(content: str) -> dict[str, list[str]]:
    """Inventory runtime and dev package names in a Composer lockfile.

    Malformed records fail closed instead of causing an incomplete inventory.
    Error strings are intentionally constant and never include lockfile values.
    """
    try:
        validate_json_nesting(content)
        document = json.loads(
            content.removeprefix('\ufeff'),
            object_pairs_hook=_unique_object_keys,
            parse_constant=_reject_nonfinite_number,
            parse_float=parse_finite_json_float,
        )
    except (json.JSONDecodeError, ValueError, RecursionError, OverflowError):
        raise ValueError('invalid composer.lock JSON') from None
    if not isinstance(document, dict):
        raise ValueError('composer.lock root must be an object')

    groups: dict[str, list[str]] = {}
    for section, group in (('packages', 'locked'), ('packages-dev', 'locked-dev')):
        entries = document.get(section, [])
        if not isinstance(entries, list):
            raise ValueError(f'composer.lock {section} must be an array')
        names: set[str] = set()
        for package in entries:
            if not isinstance(package, dict):
                raise ValueError(f'composer.lock {section} has invalid package records')
            name = package.get('name')
            if (not isinstance(name, str) or len(name) > _MAX_NAME_LENGTH
                    or not _PACKAGE_NAME.fullmatch(name)):
                raise ValueError(f'composer.lock {section} has invalid package names')
            canonical = name.lower()
            if canonical in names:
                raise ValueError(f'composer.lock {section} has duplicate package names')
            names.add(canonical)
        if names:
            groups[group] = sorted(names)
    return groups
