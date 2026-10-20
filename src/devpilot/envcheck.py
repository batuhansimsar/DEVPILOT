"""Bounded, read-only .env key comparison that never reports secret values."""

from __future__ import annotations

import re
import stat
from pathlib import Path
from typing import Any

TEMPLATES = ('.env.example', '.env.sample', '.env.template')
MAX_ENV_BYTES = 256 * 1024
_KEY = re.compile(r'[A-Za-z_][A-Za-z0-9_]*\Z')


def _keys(path: Path) -> tuple[set[str] | None, str | None]:
    """Read variable names only; refuse symlinks, non-files and huge files."""
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
    try:
        with path.open('rb') as handle:
            raw = handle.read(MAX_ENV_BYTES + 1)
    except OSError:
        return None, 'not readable'
    if len(raw) > MAX_ENV_BYTES:
        return None, 'exceeds 256 KiB limit'
    names: set[str] = set()
    for line in raw.decode('utf-8', errors='replace').splitlines():
        line = line.strip()
        if line.startswith('export '):
            line = line[7:].lstrip()
        key, separator, _ = line.partition('=')
        if separator and _KEY.fullmatch(key.strip()):
            names.add(key.strip())
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
