"""Read-only checks for accidentally committed environment configuration.

Never opens environment files, and never prints their contents.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .secret_audit import MAX_OUTPUT, MAX_PATHS, _tracked_paths
from .walk import _printable

SAFE_ENV_NAMES = frozenset({'.env.example', '.env.sample', '.env.template', '.env.dist', '.env.defaults'})
SAFE_ENV_TEMPLATE_SUFFIXES = ('.example', '.sample', '.template', '.dist', '.defaults')


def tracked_environment_files(root: Path) -> list[str]:
    """List staged or committed .env* files without unbounded Git buffering.

    Reuse the bounded, hook-disabled Git index reader. Missing Git, unreadable
    indexes and malformed/oversized results return no findings as before.
    No tracked file contents are opened.
    """
    if shutil.which('git') is None:
        return []
    try:
        raw = _tracked_paths(root)
    except RuntimeError:
        return []
    # Never interpret partial or malformed NUL-delimited index output as
    # complete, and bound processing even when the reader is mocked.
    if len(raw) > MAX_OUTPUT or raw.count(b'\0') > MAX_PATHS or (
        raw and (not raw.endswith(b'\0') or raw.startswith(b'\0') or b'\0\0' in raw)
    ):
        return []
    paths = raw.decode('utf-8', errors='surrogateescape').split('\0')
    return sorted({
        _printable(path) for path in paths if path and
        (name := Path(path).name.lower()).startswith('.env') and not (
            name in SAFE_ENV_NAMES or
            (name.startswith('.env.') and name.endswith(SAFE_ENV_TEMPLATE_SUFFIXES))
        )
    })
