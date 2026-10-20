"""Read-only filename-based checks for potentially committed credentials."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from typing import Any

_PRIVATE_NAMES = frozenset({
    'id_rsa', 'id_dsa', 'id_ed25519', 'id_ecdsa', 'credentials.json',
    'service-account.json', '.pypirc', '.npmrc', 'secrets.yml', 'secrets.yaml',
})
_PRIVATE_EXTENSIONS = frozenset({'.pem', '.key', '.p12', '.pfx', '.kdbx', '.keystore'})
_ENV_EXAMPLES = frozenset({'.env.example', '.env.sample', '.env.template', '.env.dist', '.env.defaults'})


def _potential_secret(path: str) -> bool:
    name = Path(path).name.lower()
    if name in _ENV_EXAMPLES:
        return False
    if name == '.env' or name.startswith('.env.'):
        return True
    return name in _PRIVATE_NAMES or Path(name).suffix in _PRIVATE_EXTENSIONS


def audit_tracked_files(root: Path) -> dict[str, Any]:
    """Check Git's index only; never open candidate files or print secret values."""
    report: dict[str, Any] = {'path': str(root), 'tracked_files': 0, 'candidates': [], 'truncated': False}
    if not shutil.which('git'):
        report['error'] = 'Git is not installed'
        return report
    try:
        completed = subprocess.run(
            ['git', '-C', str(root), '--no-optional-locks', 'ls-files', '--cached', '-z'],
            capture_output=True, timeout=10, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        report['error'] = f'Cannot inspect Git index: {exc}'
        return report
    if completed.returncode:
        report['error'] = 'Not a readable Git worktree'
        return report
    paths = completed.stdout.split(b'\0')
    for raw in paths:
        if not raw:
            continue
        report['tracked_files'] += 1
        name = raw.decode('utf-8', 'replace')
        if _potential_secret(name):
            if len(report['candidates']) < 50:
                report['candidates'].append(name)
            else:
                report['truncated'] = True
    report['candidates'].sort()
    return report
