"""Read-only repository discovery and guarded local command execution."""

from __future__ import annotations

import json
import os
import signal
import shutil
import socket
import sys
from collections import Counter
from pathlib import Path

from .bounded_process import run_bounded
from .envcheck import inspect_env
from typing import Any

from .gradle import gradle_test_command
from .manifest import MAX_MANIFEST_BYTES, read_package_json as _read_package_json
from .node import LOCKFILES, package_manager
from .walk import walk_project

SKIP_DIRS = frozenset({
    '.git', '.hg', '.svn', '.venv', 'venv', 'env', '__pycache__',
    'node_modules', 'dist', 'build', '.next', '.nuxt', '.turbo',
    'coverage', '.pytest_cache', '.mypy_cache', '.ruff_cache',
    'target', 'bin', 'obj', 'vendor', '.idea', '.vs',
})
LANGUAGES = {
    '.py': 'Python', '.js': 'JavaScript', '.jsx': 'JavaScript',
    '.mjs': 'JavaScript', '.cjs': 'JavaScript',
    '.ts': 'TypeScript', '.tsx': 'TypeScript',
    '.mts': 'TypeScript', '.cts': 'TypeScript', '.cs': 'C#',
    '.go': 'Go', '.rs': 'Rust', '.java': 'Java', '.kt': 'Kotlin',
    '.swift': 'Swift', '.rb': 'Ruby', '.php': 'PHP', '.cpp': 'C++',
    '.cc': 'C++', '.c': 'C', '.h': 'C/C++', '.vue': 'Vue',
    '.svelte': 'Svelte', '.astro': 'Astro', '.html': 'HTML', '.css': 'CSS', '.sql': 'SQL',
    '.sh': 'Shell', '.ps1': 'PowerShell',
}
KEY_FILES = frozenset({
    'package.json', 'pyproject.toml', 'requirements.txt', 'setup.py',
    'go.mod', 'Cargo.toml', 'pom.xml', 'build.gradle', 'build.gradle.kts',
    'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
    'compose.yml', 'compose.yaml', '.gitignore', 'Makefile',
    'README.md', 'LICENSE', 'LICENSE.md', '.env.example',
})
MAX_FILES = 10000
MAX_DEPTH = 12

def _root_files(root: Path) -> set[str]:
    try:
        return {p.name for p in root.iterdir() if p.is_file() and not p.is_symlink()}
    except OSError:
        return set()


def _node_test_argv(root: Path, package: dict[str, Any]) -> list[str]:
    """Select a safe package script runner without executing any project code.

    Ambiguous lockfiles without an explicit packageManager must be resolved
    by the developer before tests can be executed.
    """
    manager, lockfiles, declared = package_manager(root, package)
    if not declared and len({LOCKFILES[name] for name in lockfiles}) > 1:
        return []
    return ['bun', 'run', 'test'] if manager == 'bun' else [manager, 'test']


def detect_projects(root: Path) -> list[str]:
    names = _root_files(root)
    types: set[str] = set()
    if 'package.json' in names:
        types.add('Node.js')
    if names & {'pyproject.toml', 'requirements.txt', 'setup.py', 'Pipfile'}:
        types.add('Python')
    if names & {'Cargo.toml'}:
        types.add('Rust')
    if 'go.mod' in names:
        types.add('Go')
    if names & {'pom.xml', 'build.gradle', 'build.gradle.kts'}:
        types.add('Java')
    if any(Path(name).suffix.lower() in {'.csproj', '.sln', '.slnx', '.fsproj', '.vbproj'} for name in names):
        types.add('.NET')
    if names & {'Dockerfile', 'compose.yml', 'compose.yaml', 'docker-compose.yml', 'docker-compose.yaml'}:
        types.add('Docker')
    return sorted(types)


def analyze_project(root: Path) -> dict[str, Any]:
    languages: Counter[str] = Counter()
    count = 0
    truncated = False
    key_files: list[str] = []
    problems: list[str] = []
    # Do not follow symlinks or recurse into generated/dependency folders.
    for current, dirs, files in walk_project(root, problems):
        here = Path(current)
        relative = here.relative_to(root)
        depth = len(relative.parts)
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not (here / d).is_symlink() and depth < MAX_DEPTH)
        for filename in sorted(files):
            p = here / filename
            if p.is_symlink() or not p.is_file():
                continue
            count += 1
            if count > MAX_FILES:
                truncated = True
                break
            language = LANGUAGES.get(p.suffix.lower())
            if language:
                languages[language] += 1
            rel = p.relative_to(root).as_posix()
            if filename in KEY_FILES and (depth == 0 or rel.startswith('.github/workflows/')):
                key_files.append(rel)
            if rel.startswith('.github/workflows/') and p.suffix.lower() in {'.yml', '.yaml'}:
                key_files.append(rel)
        if truncated:
            break
    package, error = _read_package_json(root)
    if error:
        problems.append(error)
    if package is not None:
        _, lockfiles, declared = package_manager(root, package)
        if not declared and len({LOCKFILES[name] for name in lockfiles}) > 1:
            problems.append(
                'Conflicting Node.js lockfiles detected; declare packageManager in package.json '
                'or remove obsolete lockfiles before running tests.'
            )
    scripts = package.get('scripts', {}) if package else {}
    if not isinstance(scripts, dict):
        problems.append('package.json scripts must be an object')
        scripts = {}
    return {
        'path': str(root), 'project_types': detect_projects(root),
        'file_count': min(count, MAX_FILES), 'truncated': truncated,
        'languages': dict(sorted(languages.items(), key=lambda item: (-item[1], item[0]))),
        'key_files': sorted(set(key_files)),
        'npm_scripts': sorted(k for k, v in scripts.items() if isinstance(k, str) and isinstance(v, str)),
        'problems': problems,
    }


def test_commands(root: Path) -> list[dict[str, Any]]:
    names = _root_files(root)
    commands: list[dict[str, Any]] = []
    package, _ = _read_package_json(root)
    if package:
        scripts = package.get('scripts')
        if isinstance(scripts, dict) and isinstance(scripts.get('test'), str):
            if scripts['test'].strip():
                # npm scripts execute project code. CLI requires explicit --yes.
                argv = _node_test_argv(root, package)
                if argv:
                    commands.append({'ecosystem': 'Node.js', 'argv': argv, 'reason': 'package.json test script'})
    if 'Cargo.toml' in names:
        commands.append({'ecosystem': 'Rust', 'argv': ['cargo', 'test'], 'reason': 'Cargo.toml'})
    if 'go.mod' in names:
        commands.append({'ecosystem': 'Go', 'argv': ['go', 'test', './...'], 'reason': 'go.mod'})
    # Prefer a unique solution, otherwise a unique project. Do not guess in
    # directories with multiple candidate build targets.
    solutions = sorted(name for name in names if Path(name).suffix.lower() in {'.sln', '.slnx'})
    projects = sorted(name for name in names if Path(name).suffix.lower() in {'.csproj', '.fsproj', '.vbproj'})
    dotnet_target = (solutions[0] if len(solutions) == 1 else
                     projects[0] if not solutions and len(projects) == 1 else None)
    if dotnet_target:
        commands.append({'ecosystem': '.NET', 'argv': ['dotnet', 'test', dotnet_target],
                         'reason': 'unique .NET solution/project'})
    if names & {'pyproject.toml', 'requirements.txt', 'setup.py'} and (root / 'tests').is_dir():
        if (root / 'tests').is_symlink():
            pass
        elif shutil.which('pytest'):
            commands.append({'ecosystem': 'Python', 'argv': [sys.executable, '-m', 'pytest'], 'reason': 'tests directory (pytest available)'})
        else:
            commands.append({'ecosystem': 'Python', 'argv': [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'], 'reason': 'tests directory'})
    if 'pom.xml' in names:
        commands.append({'ecosystem': 'Java', 'argv': ['mvn', 'test'], 'reason': 'pom.xml'})
    elif names & {'build.gradle', 'build.gradle.kts'}:
        argv, reason = gradle_test_command(root, names, os.name)
        commands.append({'ecosystem': 'Java', 'argv': argv, 'reason': reason})
    return commands


def doctor_report(root: Path) -> dict[str, Any]:
    found = detect_projects(root)
    tool_map = {
        'Node.js': 'node', 'Python': 'python', 'Rust': 'cargo',
        'Go': 'go', 'Java': 'java', '.NET': 'dotnet', 'Docker': 'docker',
    }
    tools = [{'name': name, 'available': bool(shutil.which(name)), 'required_by': sorted(k for k, v in tool_map.items() if v == name and k in found)}
             for name in sorted(set(tool_map.values()) | {'git'})]
    issues = analyze_project(root)['problems']
    from .security import tracked_environment_files
    tracked_env = tracked_environment_files(root)
    if tracked_env:
        shown = ', '.join(tracked_env[:5])
        if len(tracked_env) > 5:
            shown += f' (+{len(tracked_env) - 5} more)'
        issues.append('Git-tracked environment files may contain secrets: ' + shown)
    environment = inspect_env(root)
    if 'Node.js' in found:
        package, _ = _read_package_json(root)
        if package is not None:
            manager, lockfiles, declared = package_manager(root, package)
            families = {LOCKFILES[name] for name in lockfiles}
            if len(families) > 1:
                issues.append('Conflicting JavaScript lockfiles: ' + ', '.join(lockfiles))
            if declared and families and declared not in families:
                issues.append(f'packageManager specifies {declared} but lockfile(s) indicate {", ".join(sorted(families))}')
            tools.append({'name': manager, 'available': bool(shutil.which(manager)), 'required_by': ['Node.js']})
    missing = [t['name'] for t in tools if t['required_by'] and not t['available']]
    return {'path': str(root), 'project_types': found, 'tools': tools,
            'environment': environment, 'warnings': issues + [f'Missing {name} required by detected project' for name in missing],
            'ok': not issues and not missing}



def command_result(argv: list[str], root: Path, timeout: int = 15) -> dict[str, Any]:
    """Execute a local command with bounded in-memory stdout/stderr capture."""
    return run_bounded(argv, root, timeout)


def git_status(root: Path) -> dict[str, Any]:
    # Git status may execute a repository-configured fsmonitor helper.
    # Disable it and avoid optional index writes in read-only inspections.
    result = command_result([
        'git', '--no-optional-locks', '-c', 'core.fsmonitor=false',
        'status', '--short', '--branch', '--untracked-files=normal',
    ], root)
    return {'path': str(root), **result}


def docker_status(root: Path) -> dict[str, Any]:
    result = command_result(['docker', 'ps', '--format', '{{json .}}'], root)
    containers: list[dict[str, Any]] = []
    if result.get('stdout_truncated'):
        return {'containers': containers, **result, 'exit_code': 1,
                'error': 'Docker output exceeded capture limit; JSON report incomplete'}
    if result.get('exit_code') == 0:
        for line in result['stdout'].splitlines():
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    containers.append({k: obj.get(k) for k in ('Names', 'Image', 'Status', 'Ports', 'State')})
            except json.JSONDecodeError:
                result['error'] = 'Docker returned an unexpected response'
                result['exit_code'] = 1
                break
    return {'containers': containers, **result}


def tcp_check(host: str, port: int, timeout: float) -> dict[str, Any]:
    if not 1 <= port <= 65535:
        raise ValueError('port must be between 1 and 65535')
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {'host': host, 'port': port, 'reachable': True}
    except (OSError, TimeoutError) as exc:
        return {'host': host, 'port': port, 'reachable': False, 'error': str(exc)}
