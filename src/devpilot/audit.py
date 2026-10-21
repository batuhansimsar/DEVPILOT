"""Read-only filename-based checks for potentially committed credentials."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
import shutil
from typing import Any

from .firebase_credentials import is_firebase_service_account_key
from .publish_profiles import is_publish_profile, is_azure_publish_settings
from .secret_audit import _tracked_paths
from .editor_backups import strip_editor_backups
from .cargo_credentials import is_cargo_credential_location

_PRIVATE_NAMES = frozenset({
    'id_rsa', 'id_dsa', 'id_ed25519', 'id_ecdsa',
    # OpenSSH hardware-backed security keys also have sensitive private stubs.
    'id_ed25519_sk', 'id_ecdsa_sk', 'credentials.json',
    'service-account.json', 'service_account.json', 'google-credentials.json',
    'application_default_credentials.json',
    'secrets.json', '.netrc', '.envrc', '.git-credentials',
    # Ansible Vault can read plaintext decryption passwords from these files.
    '.vault_pass', '.vault_password', '.vault_pass.txt', 'vault-password.txt',
    '.pypirc', '.npmrc', 'secrets.yml', 'secrets.yaml', '.vault-token',
    '.terraformrc', 'credentials.tfrc.json',
    # Package registry authentication files can store reusable access tokens.
    'auth.json', '.yarnrc', '.yarnrc.yml',
    # Database client authentication files can embed reusable credentials.
    '.pgpass', '.pg_service.conf', '.htpasswd', '.my.cnf', '.mylogin.cnf',
    # Storage clients can persist long-lived cloud API keys in these files.
    '.s3cfg', '.boto', 'rclone.conf',
    # Legacy Docker registry config stores reusable registry authentication.
    '.dockercfg',
    # Kubernetes client configs and Terraform plans may hold reusable secrets.
    'kubeconfig', 'kubeconfig.yml', 'kubeconfig.yaml', 'tfplan',
})
# Apple App Store Connect .p8 and PuTTY .ppk files can contain private keys.
_PRIVATE_EXTENSIONS = frozenset({'.pem', '.key', '.p12', '.pfx', '.kdbx', '.keystore', '.jks', '.p8', '.ppk', '.keytab', '.jceks', '.bks'})
_SENSITIVE_LOCATIONS = frozenset({
    ('.aws', 'credentials'), ('.aws', 'config'), ('.kube', 'config'), ('.docker', 'config.json'),
    ('gh', 'hosts.yml'), ('gh', 'hosts.yaml'),
    ('.azure', 'accesstokens.json'), ('.azure', 'msal_token_cache.json'),
    ('.azure', 'msal_token_cache.bin'),
    ('gcloud', 'credentials.db'), ('gcloud', 'access_tokens.db'),
    # GitLab Runner configuration may hold long-lived runner auth tokens.
    ('gitlab-runner', 'config.toml'), ('.gitlab-runner', 'config.toml'),
    # GitLab CLI config may hold plaintext tokens without an OS keyring.
    ('glab-cli', 'config.yml'), ('glab-cli', 'config.yaml'),
    # Python package manager authentication files are not ordinary manifests.
    ('pypoetry', 'auth.toml'), ('pip', 'pip.conf'), ('pip', 'pip.ini'),
    # Build-tool settings can contain plaintext package registry credentials.
    ('.m2', 'settings.xml'), ('.gradle', 'gradle.properties'),
    ('nuget', 'nuget.config'),
    # Build-tool user settings may store repository tokens, encrypted passwords,
    # and feed credentials. Keep detection scoped to conventional config folders.
    ('.m2', 'settings.xml'), ('.m2', 'settings-security.xml'),
    ('.gradle', 'gradle.properties'), ('nuget', 'nuget.config'),
    # The Copilot CLI may save plaintext OAuth tokens when no keychain exists.
    ('.copilot', 'config.json'),
    # Streamlit project-local secrets are credential files, unlike generic TOML.
    ('.streamlit', 'secrets.toml'),
})
_SENSITIVE_CLI_LOCATIONS = frozenset({
    ('.config', 'gh', 'hosts.yml'),
    # Copilot editor integrations persist OAuth credentials in these JSON stores.
    ('.config', 'github-copilot', 'apps.json'),
    ('.config', 'github-copilot', 'hosts.json'),
    ('.config', 'github-copilot', 'oauth.json'),
})
# Helm stores chart repository passwords and OCI registry auth under ~/.config/helm.
# Restrict detection to conventional config paths; generic chart YAML is safe.
_HELM_CREDENTIAL_LOCATIONS = (
    ('.config', 'helm', 'repositories.yaml'),
    ('.config', 'helm', 'registry', 'config.json'),
)
# Limit age identity detection to conventional private-key config paths.
_AGE_IDENTITY_LOCATIONS = (
    ('.config', 'sops', 'age', 'keys.txt'),
    ('.config', 'age', 'keys.txt'),
)
# AWS CLI assumes-role and SSO caches contain reusable, short-lived tokens.
_CLOUD_TOKEN_CACHE_DIRS = frozenset({('.aws', 'cli', 'cache'), ('.aws', 'sso', 'cache')})
_ENV_EXAMPLES = frozenset({'.env.example', '.env.sample', '.env.template', '.env.dist', '.env.defaults'})
_ENV_TEMPLATE_SUFFIXES = ('.example', '.sample', '.template', '.dist', '.defaults')
_TERRAFORM_SENSITIVE_SUFFIXES = ('.tfvars', '.tfvars.json', '.tfstate', '.tfstate.backup', '.tfplan')
_TERRAFORM_TEMPLATE_SUFFIXES = tuple(
    sensitive + example
    for sensitive in _TERRAFORM_SENSITIVE_SUFFIXES
    for example in _ENV_TEMPLATE_SUFFIXES
)
_BACKUP_SUFFIXES = ('.bak', '.backup', '.old', '.orig', '.save', '~', '.tmp', '.swp', '.swo', '.swn')
_MAX_INDEX_BYTES = 8 * 1024 * 1024
_MAX_TRACKED_PATHS = 100_000


def _potential_secret(path: str) -> bool:
    # Git paths use '/', but accepting Windows separators makes the helper
    # cross-platform and avoids skipping imported path lists.
    parts = tuple(part.lower() for part in PurePosixPath(path.replace('\\', '/')).parts)
    if not parts:
        return False
    name = parts[-1]
    name, saw_vim_swap = strip_editor_backups(name, _BACKUP_SUFFIXES)
    parts = (*parts[:-1], name)
    if is_publish_profile(parts) or is_azure_publish_settings(parts):
        return True
    if name in _ENV_EXAMPLES or (
        (name.startswith('.env.') or '.env.' in name)
        and name.endswith(_ENV_TEMPLATE_SUFFIXES)
    ):
        return False
    # Cloudflare Workers loads local secrets from .dev.vars[.environment].
    # Example/template files are safe to track and should not trigger alerts.
    if name == '.dev.vars' or name.startswith('.dev.vars.'):
        return not name.endswith(_ENV_TEMPLATE_SUFFIXES)
    if (name == '.env' or name.startswith('.env.')
            or name.endswith('.env') or '.env.' in name):
        return True
    if name.endswith(_TERRAFORM_TEMPLATE_SUFFIXES):
        return False
    # Terraform files may have environment, timestamp, or format qualifiers
    # after the sensitive extension (for example, prod.tfvars.local).
    if (name == 'tfplan' or (
            name.startswith('tfplan.') and not name.endswith(_ENV_TEMPLATE_SUFFIXES)
        ) or any(name.endswith(suffix) or suffix + '.' in name
                 for suffix in _TERRAFORM_SENSITIVE_SUFFIXES)):
        return True
    found = (is_cargo_credential_location(parts) or name in _PRIVATE_NAMES
            or name.endswith(('.kubeconfig', '.kubeconfig.yml', '.kubeconfig.yaml'))
            or is_firebase_service_account_key(name)
            or PurePosixPath(name).suffix in _PRIVATE_EXTENSIONS
            or len(parts) >= 2 and parts[-2:] in _SENSITIVE_LOCATIONS
            or len(parts) >= 3 and parts[-3:] in _SENSITIVE_CLI_LOCATIONS
            or any(parts[-len(location):] == location for location in _HELM_CREDENTIAL_LOCATIONS)
            or any(parts[-len(location):] == location for location in _AGE_IDENTITY_LOCATIONS)
            or (len(parts) >= 4 and parts[-4:-1] in _CLOUD_TOKEN_CACHE_DIRS
                and name.endswith('.json')))
    # Vim adds an extra leading dot when creating swap copies of non-dotfiles.
    return found or (saw_vim_swap and name.startswith('.')
                     and _potential_secret('/'.join((*parts[:-1], name[1:]))))

def audit_tracked_files(root: Path) -> dict[str, Any]:
    """Check Git's index only; never open candidate files or print secret values."""
    report: dict[str, Any] = {'path': str(root), 'tracked_files': 0, 'candidates': [], 'truncated': False}
    if not shutil.which('git'):
        report['error'] = 'Git is not installed'
        return report
    # Reuse the capped streaming Git reader. capture_output=True can
    # exhaust memory *before* a subsequent output-size check is reached.
    try:
        output = _tracked_paths(root)
    except RuntimeError as exc:
        report['error'] = str(exc)
        return report
    if len(output) > _MAX_INDEX_BYTES:
        report['error'] = 'Git index output exceeds 8 MiB safety limit'
        return report
    # Treat incomplete records as errors instead of reporting a clean index.
    if output and (not output.endswith(b'\0')
                   or output.startswith(b'\0') or b'\0\0' in output):
        report['error'] = 'Malformed Git index output (unterminated or empty record)'
        return report
    paths = output.split(b'\0')
    if len(paths) - (1 if paths[-1] == b'' else 0) > _MAX_TRACKED_PATHS:
        report['error'] = 'Git index exceeds 100,000 tracked paths safety limit'
        return report
    for raw in paths:
        if not raw:
            continue
        report['tracked_files'] += 1
        # Distinct non-UTF-8 filenames must not collapse to identical replacement glyphs.
        name = raw.decode('utf-8', errors='surrogateescape')
        if _potential_secret(name):
            if len(report['candidates']) < 50:
                report['candidates'].append(name)
            else:
                report['truncated'] = True
    report['candidates'].sort()
    return report
