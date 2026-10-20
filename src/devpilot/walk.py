"""Read-only directory traversal that reports scan failures without leaking paths."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator


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
