"""Prevent dependency scans from entering paths through linked ancestors."""

from __future__ import annotations

import sys
from pathlib import Path

# Only conventional macOS root aliases may be skipped when checking ancestors.
_MACOS_SYSTEM_ALIASES = frozenset({'etc', 'tmp', 'var'})


def ensure_unlinked_scan_path(path: Path) -> None:
    """Reject selected roots and linked ancestors before canonicalization.

    The conventional macOS /etc, /tmp and /var aliases may be traversed,
    but no symlink is allowed as the selected root itself.
    """
    if path.is_symlink():
        raise ValueError('path is a symbolic link')
    absolute = path.absolute()
    filesystem_root = Path(absolute.anchor)
    for parent in absolute.parents:
        if (sys.platform == 'darwin' and parent.parent == filesystem_root
                and parent.name in _MACOS_SYSTEM_ALIASES):
            continue
        if parent.is_symlink():
            raise ValueError('path contains a symbolic link')
