"""Read-only filename-based checks for potentially committed credentials."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
import shutil
import subprocess
from typing import Any

_PRIVATE_NAMES = frozenset({
    'id_rsa', 'id_dsa', 'id_ed25519', 'id_ecdsa',
    # OpenSSH hardware-backed security keys also have sensitive private stubs.
    'id_ed25519_sk', 'id_ecdsa_sk', 'credentials.json',
    'service-account.json', 'service_account.json', 'google-credentials.json',
    'application_default_credentials.json',
    'secrets.json', '.netrc', '.envrc', '.git-credentials',
    '.pypirc', '.npmrc', 'secrets.yml', 'secrets.yaml',
    '.terraformrc', 'credentials.tfrc.json',
    # Package registry authentication files can store reusable access tokens.
    'auth.json', '.yarnrc', '.yarnrc.yml',
    # Database client authentication files can embed reusable credentials.
    '.pgpass', '.my.cnf', '.mylogin.cnf',
    # Kubernetes client configs and Terraform plans may hold reusable secrets.
    'kubeconfig', 'kubeconfig.yml', 'kubeconfig.yaml', 'tfplan',
})
_PRIVATE_EXTENSIONS = frozenset({'.pem', '.key', '.p12', '.pfx', '.kdbx', '.keystore', '.jks'})
_SENSITIVE_LOCATIONS = frozenset({
    ('.aws', 'credentials'), ('.kube', 'config'), ('.docker', 'config.json'),
    ('gh', 'hosts.yml'), ('gh', 'hosts.yaml'),
    ('.azure', 'accesstokens.json'), ('.azure', 'msal_token_cache.json'),
    ('.azure', 'msal_token_cache.bin'),
    ('gcloud', 'credentials.db'), ('gcloud', 'access_tokens.db'),
    # Python package manager authentication files are not ordinary manifests.
    ('pypoetry', 'auth.toml'), ('pip', 'pip.conf'), ('pip', 'pip.ini'),
})
_SENSITIVE_CLI_LOCATIONS = frozenset({('.config', 'gh', 'hosts.yml')})
# AWS CLI assumes-role and SSO caches contain reusable, short-lived tokens.
_CLOUD_TOKEN_CACHE_DIRS = frozenset({('.aws', 'cli', 'cache'), ('.aws', 'sso', 'cache')})
_ENV_EXAMPLES = frozenset({'.env.example', '.env.sample', '.env.template', '.env.dist', '.env.defaults'})
_ENV_TEMPLATE_SUFFIXES = ('.example', '.sample', '.template', '.dist', '.defaults')
_TERRAFORM_SENSITIVE_SUFFIXES = ('.tfvars', '.tfvars.json', '.tfstate', '.tfstate.backup', '.tfplan')
_TERRAFORM_TEMPLATE_SUFFIXES = tuple(
    sensitive + example
    for sensitive in ('.tfvars', '.tfvars.json')
    for example in _ENV_TEMPLATE_SUFFIXES
)
_BACKUP_SUFFIXES = ('.bak', '.backup', '.old', '.orig', '.save', '~', '.tmp', '.swp', '.swo')
_MAX_INDEX_BYTES = 8 * 1024 * 1024
_MAX_TRACKED_PATHS = 100_000


def _potential_secret(path: str) -> bool:
    # Git paths use '/', but accepting Windows separators makes the helper
    # cross-platform and avoids skipping imported path lists.
    parts = tuple(part.lower() for part in PurePosixPath(path.replace('\\', '/')).parts)
    if not parts:
        return False
    name = parts[-1]
    # Consume every backup suffix: 4+ nested copies must not hide a secret.
    # Each iteration removes characters, so even hostile names terminate.
    while True:
        suffix = next((suffix for suffix in _BACKUP_SUFFIXES
                       if name.endswith(suffix) and len(name) > len(suffix)), None)
        if suffix is None:
            break
        name = name[:-len(suffix)]
    parts = (*parts[:-1], name)
    if name in _ENV_EXAMPLES or (
        (name.startswith('.env.') or '.env.' in name)
        and name.endswith(_ENV_TEMPLATE_SUFFIXES)
    ):
        return False
    if (name == '.env' or name.startswith('.env.')
            or name.endswith('.env') or '.env.' in name):
        return True
    if name.endswith(_TERRAFORM_TEMPLATE_SUFFIXES):
        return False
    if name.endswith(_TERRAFORM_SENSITIVE_SUFFIXES):
        return True
    return (name in _PRIVATE_NAMES or PurePosixPath(name).suffix in _PRIVATE_EXTENSIONS
            or len(parts) >= 2 and parts[-2:] in _SENSITIVE_LOCATIONS
            or len(parts) >= 3 and parts[-3:] in _SENSITIVE_CLI_LOCATIONS
            or (len(parts) >= 4 and parts[-4:-1] in _CLOUD_TOKEN_CACHE_DIRS
                and name.endswith('.json')))

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
