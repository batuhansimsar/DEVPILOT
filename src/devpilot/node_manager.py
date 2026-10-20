"""Conservative Node package-manager discovery for test commands."""

from __future__ import annotations

from typing import Any


def _node_test_manager(package: dict[str, Any], names: set[str]) -> str | None:
    """Prefer an explicit manager or an unambiguous lockfile; never guess conflicts."""
    declared = package.get('packageManager')
    if isinstance(declared, str):
        name, separator, version = declared.partition('@')
        if separator and version and name in {'npm', 'pnpm', 'yarn', 'bun'}:
            return name
    markers = {
        'npm': {'package-lock.json', 'npm-shrinkwrap.json'},
        'pnpm': {'pnpm-lock.yaml'},
        'yarn': {'yarn.lock'},
        'bun': {'bun.lock', 'bun.lockb'},
    }
    candidates = {manager for manager, files in markers.items() if names & files}
    if len(candidates) > 1:
        return None
    return next(iter(candidates)) if candidates else 'npm'
