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
        detail = error.strerror or type(error).__name__
        problems.append(f"Cannot inspect {_printable(location)}: {_printable(detail)}")

    yield from os.walk(root, followlinks=False, onerror=onerror)
