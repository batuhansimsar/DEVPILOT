"""Read-only filename-based checks for potentially committed credentials."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
import shutil
import subprocess
from typing import Any

_PRIVATE_NAMES = frozenset({
    'id_rsa', 'id_dsa', 'id_ed25519', 'id_ecdsa', 'credentials.json',
    'service-account.json', 'service_account.json', 'google-credentials.json',
    'secrets.json', '.netrc', '.envrc',
    '.pypirc', '.npmrc', 'secrets.yml', 'secrets.yaml',
})
_PRIVATE_EXTENSIONS = frozenset({'.pem', '.key', '.p12', '.pfx', '.kdbx', '.keystore', '.jks'})
_SENSITIVE_LOCATIONS = frozenset({
    ('.aws', 'credentials'), ('.kube', 'config'), ('.docker', 'config.json'),
})
_ENV_EXAMPLES = frozenset({'.env.example', '.env.sample', '.env.template', '.env.dist', '.env.defaults'})
_ENV_TEMPLATE_SUFFIXES = ('.example', '.sample', '.template', '.dist', '.defaults')
_TERRAFORM_SENSITIVE_SUFFIXES = ('.tfvars', '.tfvars.json', '.tfstate', '.tfstate.backup')
_TERRAFORM_TEMPLATE_SUFFIXES = tuple(
    sensitive + example
    for sensitive in ('.tfvars', '.tfvars.json')
    for example in _ENV_TEMPLATE_SUFFIXES
)
_MAX_INDEX_BYTES = 8 * 1024 * 1024
_MAX_TRACKED_PATHS = 100_000


def _potential_secret(path: str) -> bool:
    # Git paths use '/', but accepting Windows separators makes the helper
    # cross-platform and avoids skipping imported path lists.
    parts = tuple(part.lower() for part in PurePosixPath(path.replace('\\', '/')).parts)
    if not parts:
        return False
    name = parts[-1]
    if name in _ENV_EXAMPLES or (
        name.startswith('.env.') and name.endswith(_ENV_TEMPLATE_SUFFIXES)
    ):
        return False
    if name == '.env' or name.startswith('.env.'):
        return True
    if name.endswith(_TERRAFORM_TEMPLATE_SUFFIXES):
        return False
    if name.endswith(_TERRAFORM_SENSITIVE_SUFFIXES):
        return True
    return (name in _PRIVATE_NAMES or PurePosixPath(name).suffix in _PRIVATE_EXTENSIONS
            or len(parts) >= 2 and parts[-2:] in _SENSITIVE_LOCATIONS)

def audit_tracked_files(root: Path) -> dict[str, Any]:
    """Check Git's index only; never open candidate files or print secret values."""
    report: dict[str, Any] = {'path': str(root), 'tracked_files': 0, 'candidates': [], 'truncated': False}
    if not shutil.which('git'):
        report['error'] = 'Git is not installed'
        return report
    try:
        completed = subprocess.run(
            ['git', '--no-optional-locks', '-c', 'core.fsmonitor=false', '-C', str(root),
             'ls-files', '--cached', '-z'],
            capture_output=True, timeout=10, check=False, stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        report['error'] = f'Cannot inspect Git index: {exc}'
        return report
    if completed.returncode:
        report['error'] = 'Not a readable Git worktree'
        return report
    if len(completed.stdout) > _MAX_INDEX_BYTES:
        report['error'] = 'Git index output exceeds 8 MiB safety limit'
        return report
    paths = completed.stdout.split(b'\0')
    if len(paths) - (1 if paths[-1] == b'' else 0) > _MAX_TRACKED_PATHS:
        report['error'] = 'Git index exceeds 100,000 tracked paths safety limit'
        return report
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
