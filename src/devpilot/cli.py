"""DevPilot command line interface."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any

from .audit import audit_tracked_files
from .httpcheck import http_check
from .env_cli import environment_status, format_environment
from .tlscheck import tls_check
from .deps import scan as dependency_scan
from .core import analyze_project, command_result, doctor_report, docker_status, git_status, tcp_check, test_commands
from .workspaces import discover_workspaces
from .test_selection import ECOSYSTEMS, select_test_commands


def _add_repo_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--path', default='.', help='Repository directory (default: current directory)')
    parser.add_argument('--json', action='store_true', help='Print machine-readable JSON')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='devpilot', description='Developer Control Center — diagnose projects safely')
    parser.add_argument('--version', action='version', version='devpilot 0.1.0')
    sub = parser.add_subparsers(dest='command', required=True)
    for name, description in (
        ('doctor', 'Check required developer tools and project configuration'),
        ('analyze', 'Inspect languages, manifests and project structure'),
        ('deps', 'Inventory dependency manifests without executing project code'),
        ('workspaces', 'Discover nested projects in a monorepo'),
        ('env', 'Compare environment variable names without exposing values'),
        ('git', 'Inspect local Git changes (read-only)'),
        ('audit', 'Find potentially sensitive filenames already tracked by Git'),
        ('docker', 'List running Docker containers (read-only)'),
        ('test', 'Discover project test commands; execute only with --yes'),
    ):
        cmd = sub.add_parser(name, help=description)
        _add_repo_flags(cmd)
        if name == 'workspaces':
            cmd.add_argument('--max-depth', type=int, default=5, help='Maximum directory depth (0-50; default 5)')
            cmd.add_argument('--max-directories', type=int, default=5000, help='Maximum directories to scan (1-100000; default 5000)')
        if name == 'git':
            cmd.add_argument('--fail-on-dirty', action='store_true',
                             help='Return exit code 1 when the working tree has changes')
        if name == 'test':
            cmd.add_argument('--ecosystem', choices=tuple(ECOSYSTEMS), help='Only discover or execute tests for this ecosystem')
            cmd.add_argument('--yes', action='store_true', help='Execute the detected test commands (runs project code)')
            cmd.add_argument('--timeout', type=int, default=120, help='Per-command timeout in seconds (1-3600)')
    health = sub.add_parser('check', help='Check TCP reachability of a host and port')
    health.add_argument('host', help='Hostname or IP address to check')
    health.add_argument('port', type=int, help='TCP port (1-65535)')
    health.add_argument('--timeout', type=float, default=3, help='Socket timeout in seconds (0.1-30)')
    health.add_argument('--json', action='store_true')
    health.add_argument('--tls', action='store_true', help='Require a verified TLS handshake')
    web_health = sub.add_parser('http', help='Probe an HTTP endpoint with a no-redirect HEAD request')
    web_health.add_argument('url', help='Absolute http(s) endpoint URL')
    web_health.add_argument('--timeout', type=float, default=3, help='Request timeout in seconds (0.1-30)')
    web_health.add_argument('--json', action='store_true', help='Print machine-readable JSON')
    return parser


def _human(command: str, output: dict[str, Any]) -> str:
    if command == 'env':
        return format_environment(output)
    if command == 'deps':
        lines = [f"Dependency inventory: {output['root']}"]
        for item in output['manifests']:
            lines.append(f"  {item['ecosystem']}: {item['path']} ({item['count']} dependencies)")
            for group, names in item['groups'].items():
                lines.append(f"    {group}: {', '.join(names) or '(none)'}")
        lines.extend(f"  Warning: {warning}" for warning in output['warnings'])
        return '\n'.join(lines)
    if command == 'analyze':
        lines = [f"Project: {output['path']}", f"Detected: {', '.join(output['project_types']) or 'unknown'}",
                 f"Files scanned: {output['file_count']}{' (limit reached)' if output['truncated'] else ''}"]
        lines += [f'  {name}: {count} files' for name, count in output['languages'].items()]
        lines += [f'  Manifest: {name}' for name in output['key_files']]
        lines += [f'  npm script: {name}' for name in output['npm_scripts']]
        lines += [f'  Warning: {problem}' for problem in output['problems']]
        return '\n'.join(lines)
    if command == 'workspaces':
        lines = [f"Workspaces in {output['path']}: {output['workspace_count']}"]
        lines += [f"  {item['path']}: {', '.join(item['ecosystems'])}" for item in output['workspaces']]
        if output['truncated']:
            lines.append('  Warning: directory scan limit reached')
        return '\n'.join(lines)
    if command == 'doctor':
        lines = [f"Project: {output['path']}", f"Detected: {', '.join(output['project_types']) or 'unknown'}"]
        lines += [f"  {'OK' if t['available'] else 'MISSING'} {t['name']}" + (f" (for {', '.join(t['required_by'])})" if t['required_by'] else ' (optional)') for t in output['tools']]
        env = output.get('environment', {})
        status = env.get('status')
        if status == 'missing_keys':
            lines.append(f"  Environment: {env['template']} keys absent in .env: {', '.join(env['missing_keys'])} (may be supplied externally)")
        elif status == 'local_absent':
            lines.append(f"  Environment: {env['template']} lists {env['expected_count']} keys; no local .env found")
        elif status in ('unreadable_template', 'unreadable_local'):
            lines.append(f"  Environment: cannot inspect {env['template']} or local .env ({env['detail']})")
        elif status == 'matched':
            lines.append(f"  Environment: names from {env['template']} are declared in .env (values not checked)")
        lines += [f'  Warning: {warning}' for warning in output['warnings']]
        return '\n'.join(lines) + ('\nDoctor: healthy' if output['ok'] else '\nDoctor: needs attention')
    if command == 'test':
        lines = [f"Tests: {'executed' if output['executed'] else 'dry run'}"]
        for item in output['commands']:
            lines.append(f"  {item['ecosystem']}: {shlex.join(item['argv'])} ({item['reason']})")
            if 'result' in item:
                result = item['result']
                lines.append(f"    Exit: {result['exit_code']}")
                if result.get('stdout'):
                    lines.append(result['stdout'].rstrip())
                if result.get('stderr'):
                    lines.append(result['stderr'].rstrip())
                if result.get('error'):
                    lines.append('    Error: ' + result['error'])
        if not output['commands']:
            lines.append('  No supported test command detected')
        if not output['executed'] and output['commands']:
            lines.append('  Use --yes to run detected project test scripts (untrusted code).')
        return '\n'.join(lines)
    if command == 'audit':
        if output.get('error'):
            return 'Audit unavailable: ' + output['error']
        lines = [f"Git files checked: {output['tracked_files']}"]
        lines += [f"  REVIEW tracked sensitive filename: {name}" for name in output['candidates']]
        if output['truncated']:
            lines.append('  More than 50 candidates found; list truncated')
        if not output['candidates']:
            lines.append('No suspicious tracked filenames detected (contents were not scanned).')
        else:
            lines.append('Review these paths; rotate exposed secrets if confirmed.')
        return '\n'.join(lines)
    if command == 'docker':
        if output.get('exit_code') != 0:
            return output.get('error') or output.get('stderr') or 'Docker failed'
        return '\n'.join(f"{x.get('Names')}: {x.get('Status')} ({x.get('Image')})" for x in output['containers']) or 'No running containers'
    if command == 'http':
        return f"{output['url']} — HTTP {output['status']}" + (' (healthy)' if output.get('healthy') else ' (unhealthy)') if output['reachable'] else f"{output['url']} — unreachable ({output.get('error', 'network error')})"
    if command == 'check':
        status = 'reachable' if output['reachable'] else 'unreachable'
        if 'tls_valid' in output:
            details = (' (TLS certificate verified; expires ' + output['expires_at'] + ')'
                       if output.get('expires_at') else
                       ' (TLS certificate verified)' if output['tls_valid'] else
                       f" (TLS verification failed: {output.get('error', 'unknown error')})")
            return f"{output['host']}:{output['port']} — {status}" + details
        return f"{output['host']}:{output['port']} — {status}" + (f" ({output['error']})" if output.get('error') else '')
    return output.get('stdout') or output.get('error') or output.get('stderr') or 'No changes'


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == 'http':
        try:
            result = http_check(args.url, args.timeout)
        except ValueError as exc:
            parser.error(str(exc))
        success = result.get('healthy', False)
    elif args.command == 'check':
        if not 0.1 <= args.timeout <= 30:
            parser.error('--timeout must be between 0.1 and 30 seconds')
        if not 1 <= args.port <= 65535:
            parser.error('port must be between 1 and 65535')
        result = tls_check(args.host, args.port, args.timeout) if args.tls else tcp_check(args.host, args.port, args.timeout)
        success = result['reachable']
    else:
        root = Path(args.path).expanduser().resolve()
        if not root.is_dir():
            parser.error(f'Not a directory: {root}')
        if args.command == 'env':
            result, success = environment_status(root)
        elif args.command == 'doctor':
            result = doctor_report(root)
            success = result['ok']
        elif args.command == 'deps':
            result = dependency_scan(root)
            success = not result['warnings']
        elif args.command == 'analyze':
            result = analyze_project(root)
            success = not result['problems']
        elif args.command == 'workspaces':
            if not 0 <= args.max_depth <= 50:
                parser.error('--max-depth must be between 0 and 50')
            if not 1 <= args.max_directories <= 100000:
                parser.error('--max-directories must be between 1 and 100000')
            result = discover_workspaces(root, max_depth=args.max_depth,
                                         max_directories=args.max_directories)
            success = True
        elif args.command == 'audit':
            result = audit_tracked_files(root)
            success = not result.get('error') and not result['candidates']
        elif args.command == 'git':
            result = git_status(root)
            success = result['exit_code'] == 0 and (not args.fail_on_dirty or result['dirty'] is False)
        elif args.command == 'docker':
            result = docker_status(root)
            success = result['exit_code'] == 0
        else:
            if not 1 <= args.timeout <= 3600:
                parser.error('--timeout must be between 1 and 3600 seconds')
            commands = select_test_commands(test_commands(root), args.ecosystem)
            result = {'path': str(root), 'executed': args.yes, 'commands': commands}
            success = bool(commands)
            if args.yes:
                for item in commands:
                    item['result'] = command_result(item['argv'], root, args.timeout)
                    if item['result']['exit_code'] != 0:
                        success = False
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(_human(args.command, result))
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
