"""Read-only JavaScript package-manager detection from trusted root metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any

LOCKFILES = {
    'pnpm-lock.yaml': 'pnpm',
    'yarn.lock': 'yarn',
    'bun.lock': 'bun',
    'bun.lockb': 'bun',
    'package-lock.json': 'npm',
    'npm-shrinkwrap.json': 'npm',
}
SUPPORTED = frozenset({'npm', 'pnpm', 'yarn', 'bun'})


def package_manager(root: Path, package: dict[str, Any]) -> tuple[str, list[str], str | None]:
    """Return (selected manager, detected lockfiles, packageManager declaration).

    Never follow symlinks and never run package-manager commands. Explicit
    packageManager metadata takes precedence; otherwise use a single lockfile
    family, falling back to npm for ambiguous or unconfigured projects.
    """
    locks = sorted(name for name in LOCKFILES if (root / name).is_file() and not (root / name).is_symlink())
    declaration = package.get('packageManager')
    declared = None
    if isinstance(declaration, str):
        candidate, separator, version = declaration.partition('@')
        if separator and version and candidate in SUPPORTED:
            declared = candidate
    families = {LOCKFILES[name] for name in locks}
    selected = declared or (next(iter(families)) if len(families) == 1 else 'npm')
    return selected, locks, declared
