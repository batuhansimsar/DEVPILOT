"""Privacy-conscious inventory of Composer dependency names."""

from __future__ import annotations

import json


def parse_composer_dependencies(content: str) -> dict[str, list[str]]:
    """Return require/require-dev package names, never version constraints or URLs."""
    manifest = json.loads(content)
    if not isinstance(manifest, dict):
        raise ValueError('composer.json root must be an object')
    groups: dict[str, list[str]] = {}
    for group in ('require', 'require-dev'):
        entries = manifest.get(group, {})
        if not isinstance(entries, dict):
            raise ValueError(f'composer.json {group} must be an object')
        if entries:
            groups[group] = sorted(key for key in entries if isinstance(key, str))
    return groups
