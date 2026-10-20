"""Read-only audit of sensitive-looking tracked Git filenames.

Run with ``python -m devpilot.secret_audit [path]``. File contents are never read.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath
from threading import Thread
from typing import Any

from .firebase_credentials import is_firebase_service_account_key
from .editor_backups import strip_editor_backups

MAX_OUTPUT = 8 * 1024 * 1024
MAX_PATHS = 100_000
TIMEOUT_SECONDS = 12
EXAMPLE_NAMES = frozenset({
    '.env.example', '.env.sample', '.env.template', '.env.defaults',
    'credentials.example.json', 'credentials.sample.json',
    'secrets.example.json', 'secrets.sample.json',
})
EXACT_NAMES = frozenset({
    'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519',
    'id_ecdsa_sk', 'id_ed25519_sk',
    'credentials.json', 'secrets.json', 'service-account.json',
    'service_account.json', 'google-credentials.json',
    'application_default_credentials.json',
    '.npmrc', '.pypirc', '.netrc', '.git-credentials',
    # Registry, database, and Terraform CLI authentication files can hold tokens.
    'auth.json', '.yarnrc', '.yarnrc.yml',
    '.pgpass', '.my.cnf', '.mylogin.cnf', '.terraformrc',
    'credentials.tfrc.json',
    'secrets.yml', 'secrets.yaml', '.envrc', '.vault-token',
    # Conventional Ansible Vault password-file names may expose encryption keys.
    '.vault_pass', '.vault_password', '.vault_pass.txt', 'vault-password.txt',
    'kubeconfig', 'kubeconfig.yml', 'kubeconfig.yaml',
    # s3cmd, Boto and rclone may persist storage credentials in these files.
    '.s3cfg', '.boto', 'rclone.conf',
    # Legacy Docker registry config stores reusable registry authentication.
    '.dockercfg',
})
# Include Apple App Store Connect and PuTTY private-key formats.
PRIVATE_SUFFIXES = ('.pem', '.p12', '.pfx', '.key', '.kdbx', '.jks', '.keystore', '.p8', '.ppk', '.jceks', '.bks')
STATE_SUFFIXES = ('.tfstate', '.tfstate.backup')
PLAN_NAMES = frozenset({'tfplan'})
PLAN_SUFFIXES = ('.tfplan',)
VARIABLE_SUFFIXES = ('.tfvars', '.tfvars.json')
TEMPLATE_SUFFIXES = ('.example', '.sample', '.template', '.dist', '.defaults')
BACKUP_SUFFIXES = ('.bak', '.backup', '.old', '.orig', '.save', '~', '.tmp', '.swp', '.swo', '.swn')
# These names are ambiguous outside their well-known secret-bearing directories.
SENSITIVE_LOCATIONS = frozenset({
    ('.aws', 'credentials'),
    ('.aws', 'config'),  # AWS profiles may embed access keys alongside settings.
    ('.kube', 'config'),
    ('.docker', 'config.json'),
    ('.azure', 'accesstokens.json'),
    ('.azure', 'msal_token_cache.json'),
    ('.azure', 'msal_token_cache.bin'),
    ('.terraform.d', 'credentials.tfrc.json'),
    ('gcloud', 'credentials.db'),
    ('gcloud', 'access_tokens.db'),
    # GitLab CLI config may hold plaintext tokens without an OS keyring.
    ('glab-cli', 'config.yml'),
    ('glab-cli', 'config.yaml'),
    # Only flag ambiguous package-manager config names in credential locations.
    ('pypoetry', 'auth.toml'),
    ('pip', 'pip.conf'),
    ('pip', 'pip.ini'),
    # These conventional build-tool settings may store registry passwords.
    ('.m2', 'settings.xml'),
    # Maven's security settings contain the encrypted master password used to
    # decrypt server credentials; protect them alongside settings.xml.
    ('.m2', 'settings-security.xml'),
    ('.gradle', 'gradle.properties'),
    ('nuget', 'nuget.config'),
    # Streamlit project-local secrets are credential files, unlike generic TOML.
    ('.streamlit', 'secrets.toml'),
})
# GitHub CLI stores OAuth tokens in this precise path.
SENSITIVE_CLI_LOCATIONS = frozenset({
    ('.config', 'gh', 'hosts.yml'),
    ('.config', 'gh', 'hosts.yaml'),
    # GitLab CLI persists authenticated hosts and tokens in this config.
    ('.config', 'glab-cli', 'config.yml'),
    ('.config', 'glab-cli', 'config.yaml'),
})

# Helm stores chart repository passwords and OCI registry auth under ~/.config/helm.
# Restrict detection to conventional config paths; generic chart YAML is safe.
HELM_CREDENTIAL_LOCATIONS = (
    ('.config', 'helm', 'repositories.yaml'),
    ('.config', 'helm', 'registry', 'config.json'),
)

# Age identity files contain private encryption keys, but keys.txt is only
# sensitive in these conventional configuration locations.
AGE_IDENTITY_LOCATIONS = (
    ('.config', 'sops', 'age', 'keys.txt'),
    ('.config', 'age', 'keys.txt'),
)

# Token files in these AWS CLI directories have arbitrary JSON filenames.
CLOUD_TOKEN_CACHE_DIRS = frozenset({('.aws', 'cli', 'cache'), ('.aws', 'sso', 'cache')})



def _matches_sensitive_extension(name: str, extensions: tuple[str, ...]) -> bool:
    """Match Terraform files including variants with trailing qualifiers.

    Template-only filenames are excluded by classify() before this check.
    A later suffix (for example, .tfvars.example.local) is not a template.
    """
    return any(name.endswith(extension) or extension + '.' in name
               for extension in extensions)

def classify(path: str) -> str | None:
    """Classify paths, not file contents. All findings require human review."""
    parts = PurePosixPath(path.replace('\\', '/').lower()).parts
    if not parts:
        return None
    name = parts[-1]
    name, saw_vim_swap = strip_editor_backups(name, BACKUP_SUFFIXES)
    parts = (*parts[:-1], name)
    if name in EXAMPLE_NAMES or name.endswith(('.example', '.sample', '.template', '.dist', '.defaults')):
        return None
    if name.endswith(tuple(suffix + example for suffix in VARIABLE_SUFFIXES for example in TEMPLATE_SUFFIXES)):
        return None
    # Cloudflare Workers loads sensitive local bindings from .dev.vars files.
    # The earlier template check excludes examples, including backed-up copies.
    if name == '.dev.vars' or name.startswith('.dev.vars.'):
        return 'potential Cloudflare Workers environment file'
    if (name == '.env' or name.startswith('.env.')
            or name.endswith('.env') or '.env.' in name):
        # Example/template names are safe only when the template suffix is final.
        # A later .local or .production suffix may contain actual credentials.
        if name.endswith(('.example', '.sample', '.template', '.dist', '.defaults')):
            return None
        return 'environment file'
    if len(parts) >= 4 and parts[-4:-1] in CLOUD_TOKEN_CACHE_DIRS and name.endswith('.json'):
        return 'potential cloud CLI token cache'
    if len(parts) >= 2 and parts[-2:] in SENSITIVE_LOCATIONS:
        return 'potential credential configuration'
    if len(parts) >= 3 and parts[-3:] in SENSITIVE_CLI_LOCATIONS:
        return 'potential credential configuration'
    if any(parts[-len(location):] == location for location in HELM_CREDENTIAL_LOCATIONS):
        return 'potential credential configuration'
    if is_firebase_service_account_key(name):
        return 'potential Firebase service account key'
    if any(parts[-len(location):] == location for location in AGE_IDENTITY_LOCATIONS):
        return 'potential age private identity'
    if name in EXACT_NAMES:
        return 'potential credential file'
    # Named kubeconfig exports often embed cluster certificates and bearer tokens.
    if name.endswith(('.kubeconfig', '.kubeconfig.yml', '.kubeconfig.yaml')):
        return 'potential Kubernetes credential configuration'
    if name.endswith('.keytab'):
        return 'potential Kerberos credential file'
    if name.endswith(PRIVATE_SUFFIXES):
        return 'potential private key or certificate'
    if _matches_sensitive_extension(name, STATE_SUFFIXES):
        return 'potential Terraform state containing secrets'
    if (name in PLAN_NAMES or name.startswith('tfplan.')
            or _matches_sensitive_extension(name, PLAN_SUFFIXES)):
        return 'potential Terraform plan containing secrets'
    if _matches_sensitive_extension(name, VARIABLE_SUFFIXES):
        return 'potential Terraform variables containing secrets'
    # Vim prepends a dot: e.g. '.credentials.json.swp' is a credentials.json copy.
    if saw_vim_swap and name.startswith('.'):
        return classify('/'.join((*parts[:-1], name[1:])))
    return None


def _tracked_paths(root: Path) -> bytes:
    """Collect a bounded Git index listing, killing Git before it can fill memory.

    A reader drains stdout concurrently to avoid pipe deadlocks. Unlike
    ``subprocess.run(capture_output=True)``, bytes beyond MAX_OUTPUT are never
    accumulated in the Python process.
    """
    argv = ['git', '-c', 'core.fsmonitor=false', '--no-optional-locks', 'ls-files', '-z', '--cached']
    try:
        process = subprocess.Popen(
            argv, cwd=root, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        raise RuntimeError('Unable to inspect Git index') from exc

    output = bytearray()
    exceeded = [False]
    read_failed = [False]

    def read_stdout() -> None:
        assert process.stdout is not None
        try:
            while chunk := process.stdout.read(8192):
                if len(output) + len(chunk) > MAX_OUTPUT:
                    exceeded[0] = True
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                    break
                output.extend(chunk)
        except OSError:
            read_failed[0] = True
        finally:
            process.stdout.close()

    reader = Thread(target=read_stdout, daemon=True)
    reader.start()
    try:
        returncode = process.wait(timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.wait()
        raise RuntimeError('Git index inspection timed out') from exc
    finally:
        reader.join(timeout=2)
    if reader.is_alive() or read_failed[0]:
        raise RuntimeError('Unable to read Git index output')
    if exceeded[0]:
        raise RuntimeError('Git index exceeds 8 MiB safety limit')
    if returncode != 0:
        raise RuntimeError('Not a readable Git worktree or Git index unavailable')
    return bytes(output)


def audit(root: Path, *, redact_paths: bool = False) -> dict[str, Any]:
    """Inspect Git's tracked filename index; never open repository files."""
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError('Not a directory: ' + str(root))
    if shutil.which('git') is None:
        raise RuntimeError('Git is not installed or is not in PATH')
    raw = _tracked_paths(root)
    # Git's -z listing must terminate each nonempty filename with NUL.
    # A partial final record or an empty record is not proof of a clean index.
    if raw and (not raw.endswith(b'\0') or raw.startswith(b'\0') or b'\0\0' in raw):
        raise RuntimeError('Malformed Git index output (unterminated or empty record)')
    raw_paths = raw.split(b'\0')
    if len(raw_paths) - 1 > MAX_PATHS:
        raise RuntimeError('Git index exceeds 100,000 path safety limit')
    findings: list[dict[str, str]] = []
    for raw_path in raw_paths:
        if not raw_path:
            continue
        # Preserve distinct invalid UTF-8 byte names for correct classification.
        path = raw_path.decode('utf-8', errors='surrogateescape')
        category = classify(path)
        if category:
            item = {'category': category, 'action': 'Review tracking; remove sensitive material from Git history and rotate exposed credentials if necessary.'}
            if not redact_paths:
                # Escape surrogate-escaped bytes, which cannot be encoded as
                # UTF-8 in JSON/terminal output. Preserve valid Unicode and
                # control characters for existing JSON consumers.
                item['path'] = ''.join(
                    f'\\u{ord(char):04x}' if 0xdc80 <= ord(char) <= 0xdcff else char
                    for char in path
                )
            findings.append(item)
    return {
        'path': '<redacted>' if redact_paths else str(root), 'tracked_files_checked': len(raw_paths) - 1,
        'findings': findings, 'ok': not findings,
        'note': 'Filenames only; no file contents inspected. Findings can include false positives.',
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='devpilot-secret-audit', description='Find tracked filenames that may expose credentials (read-only)')
    parser.add_argument('path', nargs='?', default='.', help='Local Git repository directory')
    parser.add_argument('--json', action='store_true', help='Print machine-readable JSON')
    parser.add_argument('--redact-paths', action='store_true', help='Omit tracked filenames from the report')
    args = parser.parse_args(argv)
    try:
        report = audit(Path(args.path), redact_paths=args.redact_paths)
    except (ValueError, RuntimeError) as exc:
        print('devpilot-secret-audit: ' + str(exc), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print('Scanned ' + str(report['tracked_files_checked']) + ' tracked paths; ' + str(len(report['findings'])) + ' potential risks.')
        for item in report['findings']:
            # Escape attacker-controlled filenames before writing terminal logs.
            # JSON quoting prevents ANSI sequences and newline spoofing.
            safe_path = json.dumps(item.get('path', '<redacted>'), ensure_ascii=True)
            print('  [WARN] ' + safe_path + ': ' + item['category'])
        print(report['note'])
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
