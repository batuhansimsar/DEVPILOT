"""Prevent dependency scans from entering paths through linked ancestors."""

from __future__ import annotations

import sys
from pathlib import Path

# Only conventional macOS root aliases may be skipped when checking ancestors.
_MACOS_SYSTEM_ALIASES = frozenset({'etc', 'tmp', 'var'})


def _is_macos_system_alias(parent: Path, filesystem_root: Path) -> bool:
    """Allow only Apple's conventional root aliases to /private/<name>."""
    if (sys.platform != 'darwin' or filesystem_root != Path('/')
            or parent.parent != filesystem_root
            or parent.name not in _MACOS_SYSTEM_ALIASES):
        return False
    try:
        return parent.resolve(strict=True) == filesystem_root / 'private' / parent.name
    except (OSError, RuntimeError):
        return False


def ensure_unlinked_scan_path(path: Path) -> None:
    """Reject selected roots and linked ancestors before canonicalization.

    Only macOS /etc, /tmp and /var aliases resolving to their conventional
    /private targets may be traversed. The selected root cannot be a symlink.
    """
    if path.is_symlink():
        raise ValueError('path is a symbolic link')
    absolute = path.absolute()
    filesystem_root = Path(absolute.anchor)
    for parent in absolute.parents:
        if parent.is_symlink() and not _is_macos_system_alias(parent, filesystem_root):
            raise ValueError('path contains a symbolic link')
