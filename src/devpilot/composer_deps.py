"""Privacy-conscious inventory of Composer dependency names."""

from __future__ import annotations

import json
import math
import re

# Composer dependencies are vendor/package names or platform requirements.
# Reject other JSON object keys rather than exposing arbitrary text from a
# potentially untrusted manifest in reports or terminal output.
_PACKAGE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
_PLATFORM_NAME = re.compile(
    r"(?:php(?:-[A-Za-z0-9][A-Za-z0-9_.-]*)?|hhvm|composer(?:-plugin-api|-runtime-api)?|"
    r"(?:ext|lib)-[A-Za-z0-9][A-Za-z0-9_.-]*)\Z", re.IGNORECASE,
)


def _unique_object_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject ambiguous JSON objects without echoing potentially private keys."""
    values: dict[str, object] = {}
    for key, value in pairs:
        if key in values:
            raise ValueError('composer.json contains duplicate object keys')
        values[key] = value
    return values


def _reject_nonfinite_number(_value: str) -> None:
    """Composer manifests are JSON, not Python's extended JSON constants."""
    raise ValueError('composer.json contains a non-finite JSON number')


def _parse_finite_float(value: str) -> float:
    """JSON numeric exponents must not silently overflow to infinity."""
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('composer.json contains a non-finite JSON number')
    return number


def parse_composer_dependencies(content: str) -> dict[str, list[str]]:
    """Return require/require-dev package names, never version constraints or URLs."""
    manifest = json.loads(content, object_pairs_hook=_unique_object_keys,
                          parse_constant=_reject_nonfinite_number,
                          parse_float=_parse_finite_float)
    if not isinstance(manifest, dict):
        raise ValueError('composer.json root must be an object')
    groups: dict[str, list[str]] = {}
    for group in ('require', 'require-dev'):
        entries = manifest.get(group, {})
        if not isinstance(entries, dict):
            raise ValueError(f'composer.json {group} must be an object')
        # Composer constraints must be strings; do not disclose rejected values.
        if any(not isinstance(constraint, str) for constraint in entries.values()):
            raise ValueError(f'composer.json {group} constraints must be strings')
        if any(not (_PACKAGE_NAME.fullmatch(name) or _PLATFORM_NAME.fullmatch(name))
               for name in entries):
            raise ValueError(f'composer.json {group} contains an invalid package name')
        if entries:
            groups[group] = sorted(entries)
    return groups
