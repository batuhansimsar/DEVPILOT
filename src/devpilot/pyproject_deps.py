"""Read-only dependency-name inventory for pyproject.toml.

TOML is parsed without running a build backend or resolving dependencies.
Versions, source URLs, markers and credentials are deliberately discarded.
"""

from __future__ import annotations

import re

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib

_NAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?\Z")
_REQUIREMENT = re.compile(
    r"^\s*([A-Za-z0-9][A-Za-z0-9_.-]*)(?:\s*\[[^\]\n]*\])?(?:\s*(?:[<>=!~;]|@\s*\S|$))"
)
_SEPARATORS = re.compile(r"[-_.]+")


def _canonical(name: str) -> str:
    return _SEPARATORS.sub("-", name).lower()


def _requirements(entries: object, label: str) -> set[str]:
    """Only return valid names, never a potentially credential-bearing value."""
    if not isinstance(entries, list):
        raise ValueError(f"pyproject.toml {label} must be a list")
    found: set[str] = set()
    for entry in entries:
        if not isinstance(entry, str):
            raise ValueError(f"pyproject.toml {label} contains an invalid requirement")
        match = _REQUIREMENT.match(entry)
        if not match:
            raise ValueError(f"pyproject.toml {label} contains an invalid requirement")
        found.add(_canonical(match.group(1)))
    return found


def _mapping(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"pyproject.toml {label} must be a table")
    return value


def parse_pyproject_dependencies(content: str) -> dict[str, list[str]]:
    """Inventory PEP 621, PEP 735, Poetry and PDM declaration names.

    Groups are kept separate for actionable reports. Poetry's python key
    is a runtime constraint, not a package. All result values are names only.
    """
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError as exc:
        # Parser diagnostics might contain untrusted text; never echo it.
        raise ValueError('Invalid pyproject.toml TOML') from exc

    found: dict[str, set[str]] = {}

    def collect(label: str, values: set[str]) -> None:
        found.setdefault(label, set()).update(values)

    if 'project' in data:
        project = _mapping(data['project'], 'project')
        if 'dependencies' in project:
            collect('dependencies', _requirements(project['dependencies'], 'project.dependencies'))
        if 'optional-dependencies' in project:
            optional = _mapping(project['optional-dependencies'], 'project.optional-dependencies')
            for group, values in optional.items():
                collect(f'optional:{group}', _requirements(values, 'project.optional-dependencies'))

    if 'dependency-groups' in data:
        groups = _mapping(data['dependency-groups'], 'dependency-groups')
        resolved: dict[str, set[str]] = {}
        visiting: set[str] = set()

        def resolve(group: str) -> set[str]:
            if group in resolved:
                return resolved[group]
            if group in visiting:
                raise ValueError('pyproject.toml dependency-groups contain an inclusion cycle')
            if group not in groups:
                raise ValueError('pyproject.toml dependency-groups reference an unknown group')
            visiting.add(group)
            entries = groups[group]
            if not isinstance(entries, list):
                raise ValueError('pyproject.toml dependency-groups must contain lists')
            names: set[str] = set()
            for entry in entries:
                if isinstance(entry, dict) and set(entry) == {'include-group'} and isinstance(entry['include-group'], str):
                    names.update(resolve(entry['include-group']))
                else:
                    names.update(_requirements([entry], 'dependency-groups'))
            visiting.remove(group)
            resolved[group] = names
            return names

        for group in groups:
            collect(f'group:{group}', resolve(group))

    tool = _mapping(data.get('tool', {}), 'tool')
    if 'poetry' in tool:
        poetry = _mapping(tool['poetry'], 'tool.poetry')
        if 'dependencies' in poetry:
            dependencies = _mapping(poetry['dependencies'], 'tool.poetry.dependencies')
            collect('dependencies', {_canonical(name) for name in dependencies
                                     if name.lower() != 'python' and _NAME.fullmatch(name)})
        if 'dev-dependencies' in poetry:
            legacy = _mapping(poetry['dev-dependencies'], 'tool.poetry.dev-dependencies')
            collect('group:dev', {_canonical(name) for name in legacy if _NAME.fullmatch(name)})
        if 'group' in poetry:
            groups = _mapping(poetry['group'], 'tool.poetry.group')
            for group, settings in groups.items():
                settings = _mapping(settings, 'tool.poetry.group entry')
                if 'dependencies' in settings:
                    dependencies = _mapping(settings['dependencies'], 'tool.poetry.group.dependencies')
                    collect(f'group:{group}', {_canonical(name) for name in dependencies
                                               if name.lower() != 'python' and _NAME.fullmatch(name)})

    if 'pdm' in tool:
        pdm = _mapping(tool['pdm'], 'tool.pdm')
        if 'dev-dependencies' in pdm:
            groups = _mapping(pdm['dev-dependencies'], 'tool.pdm.dev-dependencies')
            for group, values in groups.items():
                collect(f'group:{group}', _requirements(values, 'tool.pdm.dev-dependencies'))

    return {group: sorted(names) for group, names in sorted(found.items())}
