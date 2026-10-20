"""Read-only JavaScript package-manager detection from trusted root metadata."""

from __future__ import annotations

import unicodedata
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
    family, then pnpm workspace or Yarn configuration when no lockfiles exist.
    Ambiguous or unconfigured projects fall back to npm.
    """
    locks = sorted(name for name in LOCKFILES if (root / name).is_file() and not (root / name).is_symlink())
    declaration = package.get('packageManager')
    declared = None
    if isinstance(declaration, str):
        candidate, separator, version = declaration.partition('@')
        # Metadata comes from a repository: reject malformed/visually hidden
        # version strings before allowing them to override lockfile detection.
        valid_version = (
            0 < len(version) <= 128
            and not any(ch.isspace() or unicodedata.category(ch).startswith('C') for ch in version)
        )
        if separator and candidate in SUPPORTED and valid_version:
            declared = candidate
    families = {LOCKFILES[name] for name in locks}
    workspace = root / 'pnpm-workspace.yaml'
    pnpm_workspace = workspace.is_file() and not workspace.is_symlink()
    yarn_config = root / '.yarnrc.yml'
    yarn_config_present = yarn_config.is_file() and not yarn_config.is_symlink()
    if declared:
        selected = declared
    elif len(families) == 1:
        selected = next(iter(families))
    elif not families and pnpm_workspace:
        selected = 'pnpm'
    elif not families and yarn_config_present:
        selected = 'yarn'
    else:
        selected = 'npm'
    return selected, locks, declared
