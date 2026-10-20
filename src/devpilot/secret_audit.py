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
    'secrets.yml', 'secrets.yaml', '.envrc',
    'kubeconfig', 'kubeconfig.yml', 'kubeconfig.yaml',
})
PRIVATE_SUFFIXES = ('.pem', '.p12', '.pfx', '.key', '.kdbx', '.jks', '.keystore')
STATE_SUFFIXES = ('.tfstate', '.tfstate.backup')
PLAN_NAMES = frozenset({'tfplan'})
PLAN_SUFFIXES = ('.tfplan',)
VARIABLE_SUFFIXES = ('.tfvars', '.tfvars.json')
TEMPLATE_SUFFIXES = ('.example', '.sample', '.template', '.dist', '.defaults')
BACKUP_SUFFIXES = ('.bak', '.backup', '.old', '.orig', '.save', '~')
# These names are ambiguous outside their well-known secret-bearing directories.
SENSITIVE_LOCATIONS = frozenset({
    ('.aws', 'credentials'),
    ('.kube', 'config'),
    ('.docker', 'config.json'),
    ('.azure', 'accesstokens.json'),
    ('.azure', 'msal_token_cache.json'),
    ('.azure', 'msal_token_cache.bin'),
    ('.terraform.d', 'credentials.tfrc.json'),
    ('gcloud', 'credentials.db'),
    ('gcloud', 'access_tokens.db'),
    # Only flag ambiguous package-manager config names in credential locations.
    ('pypoetry', 'auth.toml'),
    ('pip', 'pip.conf'),
    ('pip', 'pip.ini'),
})
# GitHub CLI stores OAuth tokens in this precise path.
SENSITIVE_CLI_LOCATIONS = frozenset({
    ('.config', 'gh', 'hosts.yml'),
    ('.config', 'gh', 'hosts.yaml'),
    # GitLab CLI persists authenticated hosts and tokens in this config.
    ('.config', 'glab-cli', 'config.yml'),
    ('.config', 'glab-cli', 'config.yaml'),
})

# Token files in these AWS CLI directories have arbitrary JSON filenames.
CLOUD_TOKEN_CACHE_DIRS = frozenset({('.aws', 'cli', 'cache'), ('.aws', 'sso', 'cache')})


def classify(path: str) -> str | None:
    """Classify paths, not file contents. All findings require human review."""
    parts = PurePosixPath(path.replace('\\', '/').lower()).parts
    if not parts:
        return None
    name = parts[-1]
    # Consume all nested backup suffixes so deeper copies cannot evade audit.
    # The name strictly shrinks on every iteration, guaranteeing termination.
    while True:
        suffix = next((suffix for suffix in BACKUP_SUFFIXES
                       if name.endswith(suffix) and len(name) > len(suffix)), None)
        if suffix is None:
            break
        name = name[:-len(suffix)]
    parts = (*parts[:-1], name)
    if name in EXAMPLE_NAMES or name.endswith(('.example', '.sample', '.template', '.dist', '.defaults')):
        return None
    if name.endswith(tuple(suffix + example for suffix in VARIABLE_SUFFIXES for example in TEMPLATE_SUFFIXES)):
        return None
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
    if name in EXACT_NAMES:
        return 'potential credential file'
    if name.endswith(PRIVATE_SUFFIXES):
        return 'potential private key or certificate'
    if name.endswith(STATE_SUFFIXES):
        return 'potential Terraform state containing secrets'
    if name in PLAN_NAMES or name.endswith(PLAN_SUFFIXES):
        return 'potential Terraform plan containing secrets'
    if name.endswith(('.tfvars', '.tfvars.json')):
        return 'potential Terraform variables containing secrets'
    if name.endswith(VARIABLE_SUFFIXES):
        return 'potential Terraform variables containing secrets'
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
    raw_paths = _tracked_paths(root).split(b'\0')
    if len(raw_paths) - 1 > MAX_PATHS:
        raise RuntimeError('Git index exceeds 100,000 path safety limit')
    findings: list[dict[str, str]] = []
    for raw_path in raw_paths:
        if not raw_path:
            continue
        path = raw_path.decode('utf-8', errors='replace')
        category = classify(path)
        if category:
            item = {'category': category, 'action': 'Review tracking; remove sensitive material from Git history and rotate exposed credentials if necessary.'}
            if not redact_paths:
                item['path'] = path
            findings.append(item)
    return {
        'path': str(root), 'tracked_files_checked': len(raw_paths) - 1,
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
