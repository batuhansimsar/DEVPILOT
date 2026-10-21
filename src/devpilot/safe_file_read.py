"""Bounded reads of untrusted manifest files without following swapped links."""

from __future__ import annotations

import os
import stat
from pathlib import Path


def _identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    """Properties that change on replacement or ordinary in-place writes."""
    return (metadata.st_dev, metadata.st_ino, metadata.st_size,
            metadata.st_mtime_ns, metadata.st_ctime_ns)


def read_bounded_regular_file(path: Path, max_bytes: int) -> bytes | None:
    """Read a stable regular file with a size cap, or fail closed.

    Refuse symlinks, FIFOs, device files, and mutations between inspection and
    read. O_NONBLOCK prevents a substituted FIFO from stalling the process;
    descriptor checks protect platforms without O_NOFOLLOW.
    """
    # Reject malformed arguments before touching the filesystem. Fractional
    # budgets can raise in read(); bool is an int subclass, not a byte limit.
    if not isinstance(path, Path) or type(max_bytes) is not int or max_bytes < 0:
        return None
    try:
        initial = path.lstat()
        if not stat.S_ISREG(initial.st_mode) or initial.st_size > max_bytes:
            return None
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
        with os.fdopen(os.open(path, flags), 'rb') as stream:
            opened = os.fstat(stream.fileno())
            if (not stat.S_ISREG(opened.st_mode)
                    or opened.st_size > max_bytes
                    or _identity(opened) != _identity(initial)):
                return None
            content = stream.read(max_bytes + 1)
            if len(content) > max_bytes or _identity(os.fstat(stream.fileno())) != _identity(opened):
                return None
        return content
    except (OSError, ValueError, TypeError):
        # Malformed paths (including NUL) must fail closed without leaking text.
        return None
