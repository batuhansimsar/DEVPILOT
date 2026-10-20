"""Read-only directory traversal that reports scan failures without leaking paths."""

from __future__ import annotations

import os
import unicodedata
from pathlib import Path
from typing import Iterator


def _printable(text: str) -> str:
    """Escape terminal controls and bidi formatting in untrusted scan errors."""
    return ''.join(
        f'\u{ord(char):04x}' if unicodedata.category(char).startswith('C') else char
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
