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
    'credentials.json', 'secrets.json', 'service-account.json',
    'service_account.json', 'google-credentials.json',
    '.npmrc', '.pypirc', '.netrc',
    'secrets.yml', 'secrets.yaml', '.envrc',
})
PRIVATE_SUFFIXES = ('.pem', '.p12', '.pfx', '.key', '.kdbx', '.jks', '.keystore')
STATE_SUFFIXES = ('.tfstate', '.tfstate.backup')
# These names are ambiguous outside their well-known secret-bearing directories.
SENSITIVE_LOCATIONS = frozenset({
    ('.aws', 'credentials'),
    ('.kube', 'config'),
    ('.docker', 'config.json'),
})


def classify(path: str) -> str | None:
    """Classify paths, not file contents. All findings require human review."""
    parts = PurePosixPath(path.replace('\\', '/').lower()).parts
    if not parts:
        return None
    name = parts[-1]
    if name in EXAMPLE_NAMES or name.endswith(('.example', '.sample', '.template')):
        return None
    if name == '.env' or (name.startswith('.env.') and not name.startswith(('.env.example', '.env.sample', '.env.template', '.env.defaults'))):
        return 'environment file'
    if len(parts) >= 2 and parts[-2:] in SENSITIVE_LOCATIONS:
        return 'potential credential configuration'
    if name in EXACT_NAMES:
        return 'potential credential file'
    if name.endswith(PRIVATE_SUFFIXES):
        return 'potential private key or certificate'
    if name.endswith(STATE_SUFFIXES):
        return 'potential Terraform state containing secrets'
    return None


def audit(root: Path, *, redact_paths: bool = False) -> dict[str, Any]:
    """Inspect Git's tracked filename index; never open repository files."""
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValueError('Not a directory: ' + str(root))
    if shutil.which('git') is None:
        raise RuntimeError('Git is not installed or is not in PATH')
    argv = ['git', '-c', 'core.fsmonitor=false', '--no-optional-locks', 'ls-files', '-z', '--cached']
    try:
        process = subprocess.run(argv, cwd=root, capture_output=True, timeout=TIMEOUT_SECONDS, check=False, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('Git index inspection timed out') from exc
    except OSError as exc:
        raise RuntimeError('Unable to inspect Git index') from exc
    if process.returncode != 0:
        raise RuntimeError('Not a readable Git worktree or Git index unavailable')
    if len(process.stdout) > MAX_OUTPUT:
        raise RuntimeError('Git index exceeds 8 MiB safety limit')
    raw_paths = process.stdout.split(b'\0')
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
            print('  [WARN] ' + item.get('path', '<redacted>') + ': ' + item['category'])
        print(report['note'])
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
