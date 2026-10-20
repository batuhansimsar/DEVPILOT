"""Privacy-conscious inventory of Composer dependency names."""

from __future__ import annotations

import json


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


def parse_composer_dependencies(content: str) -> dict[str, list[str]]:
    """Return require/require-dev package names, never version constraints or URLs."""
    manifest = json.loads(content, object_pairs_hook=_unique_object_keys,
                          parse_constant=_reject_nonfinite_number)
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
        if entries:
            groups[group] = sorted(key for key in entries if isinstance(key, str))
    return groups
