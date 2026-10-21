"""Read-only checks for accidentally committed environment configuration.

Never opens environment files, and never prints their contents.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .secret_audit import MAX_OUTPUT, MAX_PATHS, BACKUP_SUFFIXES, _tracked_paths
from .editor_backups import strip_editor_backups
from .walk import _printable

SAFE_ENV_NAMES = frozenset({'.env.example', '.env.sample', '.env.template', '.env.dist', '.env.defaults'})
SAFE_ENV_TEMPLATE_SUFFIXES = ('.example', '.sample', '.template', '.dist', '.defaults')


def _is_sensitive_env_filename(filename: str) -> bool:
    """Match live dotenv filenames after removing known editor backup wrappers."""
    name, vim_swap = strip_editor_backups(filename.lower(), BACKUP_SUFFIXES)
    # Vim prepends a dot when swapping a dotfile (..env.swp -> .env).
    if vim_swap and name.startswith('.'):
        name = name[1:]
    return (
        (name == '.env' or name.startswith('.env.')
         or name.endswith('.env') or '.env.' in name)
        and name not in SAFE_ENV_NAMES
        and not name.endswith(SAFE_ENV_TEMPLATE_SUFFIXES)
    )


def tracked_environment_files(root: Path) -> list[str]:
    """List staged or committed dotenv files without unbounded Git buffering.

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
        _is_sensitive_env_filename(Path(path).name)
    })
