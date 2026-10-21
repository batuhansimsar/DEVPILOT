"""Prevent dependency scans from entering paths through linked ancestors."""

from __future__ import annotations

from pathlib import Path


def ensure_unlinked_scan_path(path: Path) -> None:
    """Reject explicitly selected symlinks, including in nested parent paths.

    Check before resolve(): canonicalizing first erases a caller-supplied
    symlink alias. A direct child of the filesystem anchor is excluded from
    the ancestor check because some systems provide standard aliases such as
    /var -> /private/var; the selected root itself is always checked.
    """
    if path.is_symlink():
        raise ValueError('path is a symbolic link')
    absolute = path.absolute()
    filesystem_root = Path(absolute.anchor)
    for parent in absolute.parents:
        if parent.parent == filesystem_root:
            continue
        if parent.is_symlink():
            raise ValueError('path contains a symbolic link')
