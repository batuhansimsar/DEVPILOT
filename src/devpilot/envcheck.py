"""Bounded, read-only .env key comparison that never reports secret values."""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path
from typing import Any

TEMPLATES = ('.env.example', '.env.sample', '.env.template', '.env.dist', '.env.defaults')
MAX_ENV_BYTES = 256 * 1024
_KEY = re.compile(r'[A-Za-z_][A-Za-z0-9_]*\Z')


def _has_closing_quote(text: str, quote: str) -> bool:
    """Find the end of a quoted dotenv value, respecting escaped quotes."""
    escaped = False
    for char in text:
        if escaped:
            escaped = False
        elif char == '\\':
            escaped = True
        elif char == quote:
            return True
    return False


def _keys(path: Path) -> tuple[set[str] | None, str | None]:
    """Read names only from an unchanged, regular file; never follow symlinks.

    The lstat and descriptor checks defend against a project swapping the file
    after it has been inspected. O_NONBLOCK avoids hanging on a swapped-in FIFO.
    Rechecking the open descriptor after reading detects in-place edits too.
    """
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None, None
    except OSError:
        return None, 'not readable'
    if not stat.S_ISREG(metadata.st_mode):
        return None, 'not a regular file'
    if metadata.st_size > MAX_ENV_BYTES:
        return None, 'exceeds 256 KiB limit'

    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    try:
        with os.fdopen(os.open(path, flags), 'rb') as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode):
                return None, 'file changed during inspection'
            if opened.st_size > MAX_ENV_BYTES:
                return None, 'exceeds 256 KiB limit'
            if (opened.st_dev, opened.st_ino, opened.st_size,
                    opened.st_mtime_ns, opened.st_ctime_ns) != (
                    metadata.st_dev, metadata.st_ino, metadata.st_size,
                    metadata.st_mtime_ns, metadata.st_ctime_ns):
                return None, 'file changed during inspection'
            raw = handle.read(MAX_ENV_BYTES + 1)
            after_read = os.fstat(handle.fileno())
            if after_read.st_size > MAX_ENV_BYTES or len(raw) > MAX_ENV_BYTES:
                return None, 'exceeds 256 KiB limit'
            if (after_read.st_dev, after_read.st_ino, after_read.st_size,
                    after_read.st_mtime_ns, after_read.st_ctime_ns) != (
                    opened.st_dev, opened.st_ino, opened.st_size,
                    opened.st_mtime_ns, opened.st_ctime_ns):
                return None, 'file changed during inspection'
            # Detect an in-place rewrite or append during the bounded read.
            finished = os.fstat(handle.fileno())
            if (finished.st_dev, finished.st_ino, finished.st_size, finished.st_mtime_ns, finished.st_ctime_ns) != (
                    opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns):
                return None, 'file changed during inspection'
    except OSError:
        return None, 'not readable'
    if len(raw) > MAX_ENV_BYTES:
        return None, 'exceeds 256 KiB limit'
    names: set[str] = set()
    # Only CR and LF delimit physical .env lines. Unicode NEL/LS/PS,
    # VT and FF within values must never forge additional declarations.
    quoted: str | None = None
    for line in re.split(r'\r\n|\r|\n', raw.decode('utf-8-sig', errors='replace')):
        if quoted is not None:
            if _has_closing_quote(line, quoted):
                quoted = None
            continue
        # Limit syntax whitespace to horizontal ASCII whitespace: str.strip()
        # would otherwise accept Unicode line separators before a fake key.
        line = line.strip(' \t')
        if line.startswith('export') and len(line) > 6 and line[6] in ' \t':
            line = line[6:].lstrip(' \t')
        key, separator, value = line.partition('=')
        key = key.strip(' \t')
        if separator and _KEY.fullmatch(key):
            names.add(key)
            # Dotenv supports multi-line quoted values. Lines inside a quoted
            # value are not declarations, even when they look like KEY=value.
            value = value.lstrip(' \t')
            if value.startswith(("'", '"')) and not _has_closing_quote(value[1:], value[0]):
                quoted = value[0]
    return names, None


def inspect_env(root: Path) -> dict[str, Any]:
    """Return only safe metadata and missing key names, never values."""
    for template in TEMPLATES:
        expected, problem = _keys(root / template)
        if expected is None and problem is None:
            continue
        if problem:
            return {'template': template, 'status': 'unreadable_template', 'detail': problem}
        assert expected is not None
        actual, local_problem = _keys(root / '.env')
        if local_problem:
            return {'template': template, 'status': 'unreadable_local', 'detail': local_problem,
                    'expected_count': len(expected)}
        if actual is None:
            return {'template': template, 'status': 'local_absent', 'expected_count': len(expected)}
        missing = sorted(expected - actual)
        return {'template': template, 'status': 'missing_keys' if missing else 'matched',
                'expected_count': len(expected), 'declared_count': len(actual), 'missing_keys': missing}
    return {'status': 'no_template'}
