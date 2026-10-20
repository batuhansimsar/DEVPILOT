"""Read-only checks for accidentally committed environment configuration.

Never opens environment files, and never prints their contents.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

SAFE_ENV_NAMES = frozenset({'.env.example', '.env.sample', '.env.template', '.env.dist'})


def tracked_environment_files(root: Path) -> list[str]:
    """List tracked .env* files, excluding documented sample/template files.

    Git's index is queried directly; both staged and committed paths are covered.
    A missing Git binary or non-repository directory returns no findings.
    """
    if shutil.which('git') is None:
        return []
    try:
        result = subprocess.run(
            ['git', '-C', str(root), '--no-optional-locks', '-c', 'core.fsmonitor=false',
             'ls-files', '--cached', '-z', '--', ':(icase,glob)**/.env*'],
            capture_output=True, check=False, timeout=5, stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode:
        return []
    paths = result.stdout.decode('utf-8', errors='replace').split('\0')
    return sorted({path for path in paths if path and Path(path).name.lower() not in SAFE_ENV_NAMES})
