"""DevPilot command line interface."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any

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
        ('workspaces', 'Discover nested projects in a monorepo'),
        ('git', 'Inspect local Git changes (read-only)'),
        ('docker', 'List running Docker containers (read-only)'),
        ('test', 'Discover project test commands; execute only with --yes'),
    ):
        cmd = sub.add_parser(name, help=description)
        _add_repo_flags(cmd)
        if name == 'test':
            cmd.add_argument('--ecosystem', choices=tuple(ECOSYSTEMS), help='Only discover or execute tests for this ecosystem')
            cmd.add_argument('--yes', action='store_true', help='Execute the detected test commands (runs project code)')
            cmd.add_argument('--timeout', type=int, default=120, help='Per-command timeout in seconds (1-3600)')
    health = sub.add_parser('check', help='Check TCP reachability of a host and port')
    health.add_argument('host', help='Hostname or IP address to check')
    health.add_argument('port', type=int, help='TCP port (1-65535)')
    health.add_argument('--timeout', type=float, default=3, help='Socket timeout in seconds (0.1-30)')
    health.add_argument('--json', action='store_true')
    return parser


def _human(command: str, output: dict[str, Any]) -> str:
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
    if command == 'docker':
        if output.get('exit_code') != 0:
            return output.get('error') or output.get('stderr') or 'Docker failed'
        return '\n'.join(f"{x.get('Names')}: {x.get('Status')} ({x.get('Image')})" for x in output['containers']) or 'No running containers'
    if command == 'check':
        return f"{output['host']}:{output['port']} — {'reachable' if output['reachable'] else 'unreachable'}" + (f" ({output['error']})" if output.get('error') else '')
    return output.get('stdout') or output.get('error') or output.get('stderr') or 'No changes'


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == 'check':
        if not 0.1 <= args.timeout <= 30:
            parser.error('--timeout must be between 0.1 and 30 seconds')
        if not 1 <= args.port <= 65535:
            parser.error('port must be between 1 and 65535')
        result = tcp_check(args.host, args.port, args.timeout)
        success = result['reachable']
    else:
        root = Path(args.path).expanduser().resolve()
        if not root.is_dir():
            parser.error(f'Not a directory: {root}')
        if args.command == 'doctor':
            result = doctor_report(root)
            success = result['ok']
        elif args.command == 'analyze':
            result = analyze_project(root)
            success = not result['problems']
        elif args.command == 'workspaces':
            result = discover_workspaces(root)
            success = True
        elif args.command == 'git':
            result = git_status(root)
            success = result['exit_code'] == 0
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
