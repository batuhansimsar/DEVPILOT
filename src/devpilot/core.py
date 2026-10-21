"""Read-only repository discovery and guarded local command execution."""

from __future__ import annotations

import errno
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

from .container_manifests import is_container_manifest
from .dotnet_manifests import dotnet_test_target, is_dotnet_manifest
from .gradle import gradle_test_command
from .maven import maven_test_command
from .git_state import is_git_dirty
from .tlscheck import _tls_dial_host, _validate_host_length
from .manifest import MAX_MANIFEST_BYTES, read_package_json as _read_package_json
from .julia_manifests import is_julia_manifest
from .python_tests import python_test_command
from .php_tests import php_test_command
from .cmake_tests import cmake_test_command
from .node import LOCKFILES, package_manager
from .ruby_tests import ruby_test_command
from .julia_tests import julia_test_command
from .dart_tests import dart_test_command
from .walk import walk_project
from .scan_root import ensure_unlinked_scan_path
from .requirements_names import is_requirements_manifest
from .pylock import is_pylock_manifest
from .haskell_manifests import is_haskell_manifest
from .r_manifests import is_r_manifest
from .r_tests import r_test_command

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
    '.go': 'Go', '.rs': 'Rust', '.java': 'Java', '.kt': 'Kotlin', '.kts': 'Kotlin',
    '.scala': 'Scala', '.sc': 'Scala', '.sbt': 'Scala',
    '.clj': 'Clojure', '.cljs': 'Clojure', '.cljc': 'Clojure', '.edn': 'Clojure',
    '.ex': 'Elixir', '.exs': 'Elixir',
    '.swift': 'Swift', '.rb': 'Ruby', '.php': 'PHP', '.cpp': 'C++',
    '.cc': 'C++', '.cxx': 'C++', '.hpp': 'C++', '.hh': 'C++',
    '.hxx': 'C++', '.ixx': 'C++', '.cppm': 'C++', '.ipp': 'C++',
    '.c': 'C', '.h': 'C/C++', '.vue': 'Vue',
    '.svelte': 'Svelte', '.astro': 'Astro', '.html': 'HTML', '.css': 'CSS', '.sql': 'SQL',
    '.sh': 'Shell', '.ps1': 'PowerShell',
    '.dart': 'Dart', '.jl': 'Julia', '.lua': 'Lua',
    '.r': 'R', '.rmd': 'R', '.rnw': 'R',
    '.hs': 'Haskell', '.lhs': 'Haskell',
    '.ex': 'Elixir', '.exs': 'Elixir', '.zig': 'Zig',
}
KEY_FILES = frozenset({
    'package.json', 'deno.json', 'deno.jsonc', 'deno.lock', 'pyproject.toml', 'requirements.txt', 'setup.py', 'setup.cfg', 'pytest.ini', 'tox.ini',
    'CMakeLists.txt', 'go.mod', 'Cargo.toml', 'pom.xml', 'build.sbt', 'deps.edn', 'project.clj', 'build.gradle', 'build.gradle.kts',
    'settings.gradle', 'settings.gradle.kts',
    'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
    'codefresh.yml',  # Codefresh's documented default root CI entrypoint.
    'compose.yml', 'compose.yaml', '.gitignore', 'Makefile',
    'README.md', 'LICENSE', 'LICENSE.md', '.env.example', 'Pipfile', 'Pipfile.lock',
    'uv.lock', 'poetry.lock', 'go.work',
    'global.json', 'Directory.Packages.props',
    'Directory.Build.props', 'Directory.Build.targets',
    'Gemfile', 'Gemfile.lock', 'gems.rb', 'gems.locked',
    'Package.swift', 'Package.resolved', 'mix.exs', 'mix.lock',
    'stack.yaml', 'cabal.project', 'cabal.project.freeze', 'package.yaml',
    'pubspec.yaml', 'pubspec.lock',
    'environment.yml', 'environment.yaml', 'pixi.toml', 'pixi.lock',
    'build.zig', 'build.zig.zon',
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


def _has_python_manifest(names: set[str]) -> bool:
    """Match Python project, dependency, and test-runner configuration markers."""
    return bool(names & {'pyproject.toml', 'setup.py', 'setup.cfg', 'pytest.ini', 'tox.ini', 'Pipfile', 'Pipfile.lock', 'uv.lock', 'poetry.lock'}) or any(
        is_requirements_manifest(name) or is_pylock_manifest(name)
        for name in names
    )


def detect_projects(root: Path) -> list[str]:
    names = _root_files(root)
    types: set[str] = set()
    if 'package.json' in names:
        types.add('Node.js')
    # A lockfile-only Deno workspace should agree with discover_workspaces().
    if names & {'deno.json', 'deno.jsonc', 'deno.lock'}:
        types.add('Deno')
    if _has_python_manifest(names):
        types.add('Python')
    # Both classic Conda environments and Pixi lockfile-only roots are workspaces.
    if names & {'environment.yml', 'environment.yaml', 'pixi.toml', 'pixi.lock'}:
        types.add('Conda')
    if names & {'Gemfile', 'Gemfile.lock', 'gems.rb', 'gems.locked'} or any(
            name.lower().endswith('.gemspec') for name in names):
        types.add('Ruby')
    if names & {'composer.json', 'composer.lock'}:
        types.add('PHP')
    if names & {'Cargo.toml'}:
        types.add('Rust')
    if names & {'go.mod', 'go.work'}:
        types.add('Go')
    if 'CMakeLists.txt' in names:
        types.add('C/C++')
    if 'build.sbt' in names:
        types.add('Scala')
    if names & {'build.zig', 'build.zig.zon'}:
        types.add('Zig')
    if names & {'deps.edn', 'project.clj'}:
        types.add('Clojure')
    if any(is_haskell_manifest(name) for name in names):
        types.add('Haskell')
    if 'Package.swift' in names:
        types.add('Swift')
    # A Dart lockfile-only root is still a project, matching workspace discovery.
    if names & {'pubspec.yaml', 'pubspec.lock'}:
        types.add('Dart')
    # A Mix lockfile also identifies an Elixir workspace without mix.exs.
    if names & {'mix.exs', 'mix.lock'}:
        types.add('Elixir')
    if any(is_julia_manifest(name) for name in names):
        types.add('Julia')
    if any(is_r_manifest(name) for name in names):
        types.add('R')
    # A settings-only Gradle build is still a Java project (for example,
    # a root aggregator defining subprojects in settings.gradle[.kts]).
    if names & {'pom.xml', 'build.gradle', 'build.gradle.kts',
                'settings.gradle', 'settings.gradle.kts'}:
        types.add('Java')
    if any(is_dotnet_manifest(name) for name in names):
        types.add('.NET')
    if any(is_container_manifest(name) for name in names):
        types.add('Docker')
    return sorted(types)


def analyze_project(root: Path) -> dict[str, Any]:
    # Walking a linked root is forbidden; do not inspect project manifests or
    # package metadata after the walker rejects that path.
    try:
        ensure_unlinked_scan_path(root)
    except ValueError:
        return {
            'path': str(root), 'project_types': [], 'file_count': 0,
            'truncated': True, 'languages': {}, 'key_files': [],
            'npm_scripts': [], 'problems': ['Cannot inspect .: project path contains a symbolic link'],
        }
    languages: Counter[str] = Counter()
    count = 0
    truncated = False
    file_limit_hit = False
    key_files: list[str] = []
    problems: list[str] = []
    # Do not follow symlinks or recurse into generated/dependency folders.
    for current, dirs, files in walk_project(root, problems):
        here = Path(current)
        relative = here.relative_to(root)
        depth = len(relative.parts)
        candidates = sorted(d for d in dirs if d not in SKIP_DIRS and not (here / d).is_symlink())
        if depth >= MAX_DEPTH:
            # Reaching the depth cap is incomplete only if subtrees were skipped.
            if candidates:
                truncated = True
            dirs[:] = []
        else:
            dirs[:] = candidates
        for filename in sorted(files):
            p = here / filename
            if p.is_symlink() or not p.is_file():
                continue
            count += 1
            if count > MAX_FILES:
                truncated = True
                file_limit_hit = True
                break
            language = LANGUAGES.get(p.suffix.lower())
            if language:
                languages[language] += 1
            rel = p.relative_to(root).as_posix()
            if (filename in KEY_FILES or is_requirements_manifest(filename)
                or filename.lower().endswith('.gemspec')
                or is_pylock_manifest(filename) or is_container_manifest(filename)
                or is_haskell_manifest(filename) or is_r_manifest(filename)
                or is_dotnet_manifest(filename) or is_julia_manifest(filename)) and (
                depth == 0 or rel.startswith('.github/workflows/')
            ):
                key_files.append(rel)
            if rel.startswith('.github/workflows/') and p.suffix.lower() in {'.yml', '.yaml'}:
                key_files.append(rel)
        if file_limit_hit:
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
    if names & {'deno.json', 'deno.jsonc'}:
        commands.append({'ecosystem': 'Deno', 'argv': ['deno', 'test'],
                         'reason': 'Deno configuration'})
    cmake_command = cmake_test_command(root, names)
    if cmake_command is not None:
        commands.append(cmake_command)
    if 'Cargo.toml' in names:
        commands.append({'ecosystem': 'Rust', 'argv': ['cargo', 'test'], 'reason': 'Cargo.toml'})
    php_command = php_test_command(root, names)
    if php_command is not None:
        commands.append(php_command)
    dart_command = dart_test_command(root, names)
    if dart_command is not None:
        commands.append(dart_command)
    if 'go.mod' in names:
        commands.append({'ecosystem': 'Go', 'argv': ['go', 'test', './...'], 'reason': 'go.mod'})
    if 'build.sbt' in names:
        commands.append({'ecosystem': 'Scala', 'argv': ['sbt', 'test'], 'reason': 'build.sbt'})
    if 'build.zig' in names:
        commands.append({'ecosystem': 'Zig', 'argv': ['zig', 'build', 'test'], 'reason': 'build.zig'})
    # tools.deps does not mandate a test alias. Leiningen defines `lein test`.
    if 'project.clj' in names:
        commands.append({'ecosystem': 'Clojure', 'argv': ['lein', 'test'], 'reason': 'project.clj'})
    if 'stack.yaml' in names:
        commands.append({'ecosystem': 'Haskell', 'argv': ['stack', 'test'], 'reason': 'stack.yaml'})
    elif 'cabal.project' in names or any(name.endswith('.cabal') and is_haskell_manifest(name) for name in names):
        commands.append({'ecosystem': 'Haskell', 'argv': ['cabal', 'test'], 'reason': 'Cabal project'})
    julia_command = julia_test_command(root, names)
    if julia_command is not None:
        commands.append(julia_command)
    r_command = r_test_command(root, names)
    if r_command is not None:
        commands.append(r_command)
    ruby_command = ruby_test_command(root, names)
    if ruby_command is not None:
        commands.append(ruby_command)
    if 'Package.swift' in names:
        commands.append({'ecosystem': 'Swift', 'argv': ['swift', 'test'], 'reason': 'Package.swift'})
    if 'mix.exs' in names:
        commands.append({'ecosystem': 'Elixir', 'argv': ['mix', 'test'], 'reason': 'mix.exs'})

    # Prefer a unique solution, otherwise a unique project. Do not guess in
    # directories with multiple candidate build targets.
    dotnet_target = dotnet_test_target(names)
    if dotnet_target:
        commands.append({'ecosystem': '.NET', 'argv': ['dotnet', 'test', dotnet_target],
                         'reason': 'unique .NET solution/project'})
    if _has_python_manifest(names):
        python_command = python_test_command(root)
        if python_command is not None:
            commands.append(python_command)
    if 'pom.xml' in names:
        argv, reason = maven_test_command(root, names, os.name)
        commands.append({'ecosystem': 'Java', 'argv': argv, 'reason': reason})
    elif names & {'build.gradle', 'build.gradle.kts'}:
        argv, reason = gradle_test_command(root, names, os.name)
        commands.append({'ecosystem': 'Java', 'argv': argv, 'reason': reason})
    return commands


def doctor_report(root: Path) -> dict[str, Any]:
    found = detect_projects(root)
    tool_map = {
        'Node.js': 'node', 'Deno': 'deno', 'Python': 'python', 'Rust': 'cargo',
        'Go': 'go', 'C/C++': 'ctest', 'Java': 'java', 'Scala': 'sbt', '.NET': 'dotnet', 'Docker': 'docker',
        'Ruby': 'ruby', 'Swift': 'swift', 'Elixir': 'mix', 'Dart': 'dart', 'Julia': 'julia', 'Zig': 'zig',
        'R': 'Rscript', 'PHP': 'php',
    }
    if 'Conda' in found:
        # Pixi uses its own executable; a plain environment.yml requires conda.
        tool_map['Conda'] = ('pixi' if _root_files(root) & {'pixi.toml', 'pixi.lock'} else 'conda')
    if 'Clojure' in found:
        tool_map['Clojure'] = 'lein' if 'project.clj' in _root_files(root) else 'clojure'
    if 'Haskell' in found:
        tool_map['Haskell'] = 'stack' if 'stack.yaml' in _root_files(root) else 'cabal'
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
        'status', '--porcelain=v1', '--branch', '--untracked-files=normal',
    ], root)
    dirty = is_git_dirty(result.get('stdout', ''), result['exit_code'])
    if result.get('stdout_truncated') and dirty is False:
        dirty = None  # Incomplete output cannot prove either state.
    return {'path': str(root), **result, 'dirty': dirty}


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
                if not isinstance(obj, dict):
                    raise ValueError('Expected a Docker JSON object')
            except (json.JSONDecodeError, ValueError):
                # Never expose a partial list as though it were trustworthy.
                containers.clear()
                result['error'] = 'Docker returned an unexpected response'
                result['exit_code'] = 1
                break
            containers.append({k: obj.get(k) for k in ('Names', 'Image', 'Status', 'Ports', 'State')})
    return {'containers': containers, **result}


def tcp_check(host: str, port: int, timeout: float) -> dict[str, Any]:
    """Probe a TCP endpoint after validating its explicit host and socket limits."""
    _validate_host_length(host)
    if not isinstance(host, str) or not host or any(
        char.isspace() or ord(char) < 32 or ord(char) == 127 for char in host
    ):
        raise ValueError('host must be a hostname or IP address without whitespace')
    dial_host = _tls_dial_host(host)
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('port must be between 1 and 65535')
    if (not isinstance(timeout, (int, float)) or isinstance(timeout, bool)
            or not 0.1 <= timeout <= 30):
        raise ValueError('timeout must be between 0.1 and 30 seconds')
    try:
        with socket.create_connection((dial_host, port), timeout=timeout):
            return {'host': host, 'port': port, 'reachable': True}
    except (OSError, TimeoutError) as exc:
        # Never expose OS-provided error messages: they may include internal
        # hostnames, paths or untrusted socket details in JSON/terminal reports.
        if isinstance(exc, TimeoutError):
            error = 'TCP connection timed out'
        elif isinstance(exc, ConnectionRefusedError):
            error = 'connection refused'
        else:
            error = errno.errorcode.get(exc.errno, 'network I/O error')
        return {'host': host, 'port': port, 'reachable': False, 'error': error}
