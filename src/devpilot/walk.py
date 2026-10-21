"""Read-only directory traversal that reports scan failures without leaking paths."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

from .scan_root import ensure_unlinked_scan_path


def _printable(text: str) -> str:
    """Escape all nonprinting characters in untrusted scan errors."""
    return ''.join(
        (f'\\u{ord(char):04x}' if ord(char) <= 0xffff else f'\\U{ord(char):08x}')
        if not char.isprintable() else char
        for char in text
    )


def _safe_error_detail(error: OSError) -> str:
    """Use an OS-defined description, never a potentially sensitive strerror."""
    try:
        return os.strerror(error.errno)
    except (TypeError, ValueError, OverflowError):
        return 'I/O error'


def walk_project(root: Path, problems: list[str]) -> Iterator[tuple[str, list[str], list[str]]]:
    """Traverse without following symlinks and report unreadable directories.

    os.walk ordinarily suppresses scandir errors, so ignoring its onerror
    argument makes inaccessible source folders look like an empty, complete scan.
    """
    # Preserve the specific diagnostic for an explicitly linked root.
    if root.is_symlink():
        problems.append('Cannot inspect .: project root is a symbolic link')
        return

    # Share the ancestor preflight with other scans, rejecting arbitrary
    # root-level aliases without dereferencing the selected workspace.
    try:
        ensure_unlinked_scan_path(root)
    except ValueError:
        problems.append('Cannot inspect .: project path contains a symbolic link')
        return

    def onerror(error: OSError) -> None:
        location = '.'
        if error.filename:
            try:
                relative = Path(error.filename).relative_to(root)
                location = relative.as_posix() if ".." not in relative.parts else "[outside project]"
            except (ValueError, TypeError):
                location = '[outside project]'
        problems.append(f"Cannot inspect {_printable(location)}: {_printable(_safe_error_detail(error))}")

    yield from os.walk(root, followlinks=False, onerror=onerror)
