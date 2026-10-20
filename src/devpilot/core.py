"""Read-only repository discovery and guarded local command execution."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SKIP_DIRS = frozenset({
    '.git', '.hg', '.svn', '.venv', 'venv', 'env', '__pycache__',
    'node_modules', 'dist', 'build', '.next', '.nuxt', '.turbo',
    'coverage', '.pytest_cache', '.mypy_cache', '.ruff_cache',
    'target', 'bin', 'obj', 'vendor', '.idea', '.vs',
})
LANGUAGES = {
    '.py': 'Python', '.js': 'JavaScript', '.jsx': 'JavaScript',
    '.ts': 'TypeScript', '.tsx': 'TypeScript', '.cs': 'C#',
    '.go': 'Go', '.rs': 'Rust', '.java': 'Java', '.kt': 'Kotlin',
    '.swift': 'Swift', '.rb': 'Ruby', '.php': 'PHP', '.cpp': 'C++',
    '.cc': 'C++', '.c': 'C', '.h': 'C/C++', '.vue': 'Vue',
    '.svelte': 'Svelte', '.html': 'HTML', '.css': 'CSS', '.sql': 'SQL',
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
MAX_MANIFEST_BYTES = 256 * 1024


def _read_package_json(root: Path) -> tuple[dict[str, Any] | None, str | None]:
    manifest = root / 'package.json'
    if not manifest.is_file() or manifest.is_symlink():
        return None, None
    try:
        if manifest.stat().st_size > MAX_MANIFEST_BYTES:
            return None, 'package.json exceeds the 256 KiB inspection limit'
        data = json.loads(manifest.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            return None, 'package.json must contain a JSON object'
        return data, None
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f'Invalid package.json: {exc}'


def _root_files(root: Path) -> set[str]:
    try:
        return {p.name for p in root.iterdir() if p.is_file() and not p.is_symlink()}
    except OSError:
        return set()


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
    if any(p.suffix.lower() in {'.csproj', '.sln', '.slnx', '.fsproj'} for p in root.iterdir() if p.is_file()):
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
    for current, dirs, files in os.walk(root, followlinks=False):
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
                commands.append({'ecosystem': 'Node.js', 'argv': ['npm', 'test'], 'reason': 'package.json test script'})
    if 'Cargo.toml' in names:
        commands.append({'ecosystem': 'Rust', 'argv': ['cargo', 'test'], 'reason': 'Cargo.toml'})
    if 'go.mod' in names:
        commands.append({'ecosystem': 'Go', 'argv': ['go', 'test', './...'], 'reason': 'go.mod'})
    if any(p.suffix.lower() in {'.sln', '.slnx', '.csproj', '.fsproj'} for p in root.iterdir() if p.is_file()):
        commands.append({'ecosystem': '.NET', 'argv': ['dotnet', 'test'], 'reason': '.NET solution/project'})
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
        if 'gradlew' in names:
            commands.append({'ecosystem': 'Java', 'argv': ['./gradlew', 'test'] if os.name != 'nt' else ['gradlew.bat', 'test'], 'reason': 'Gradle wrapper'})
        else:
            commands.append({'ecosystem': 'Java', 'argv': ['gradle', 'test'], 'reason': 'Gradle project'})
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
    missing = [t['name'] for t in tools if t['required_by'] and not t['available']]
    return {'path': str(root), 'project_types': found, 'tools': tools,
            'warnings': issues + [f'Missing {name} required by detected project' for name in missing],
            'ok': not issues and not missing}


def command_result(argv: list[str], root: Path, timeout: int = 15) -> dict[str, Any]:
    try:
        finished = subprocess.run(argv, cwd=root, capture_output=True, text=True,
                                  timeout=timeout, shell=False, errors='replace')
        return {'argv': argv, 'exit_code': finished.returncode,
                'stdout': finished.stdout[-20000:], 'stderr': finished.stderr[-20000:]}
    except subprocess.TimeoutExpired:
        return {'argv': argv, 'exit_code': None, 'error': f'Timed out after {timeout}s'}
    except OSError as exc:
        return {'argv': argv, 'exit_code': None, 'error': str(exc)}


def git_status(root: Path) -> dict[str, Any]:
    result = command_result(['git', 'status', '--short', '--branch', '--untracked-files=normal'], root)
    return {'path': str(root), **result}


def docker_status(root: Path) -> dict[str, Any]:
    result = command_result(['docker', 'ps', '--format', '{{json .}}'], root)
    containers: list[dict[str, Any]] = []
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
