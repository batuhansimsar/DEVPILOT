"""Safely inventory only package names from PEP 621 pyproject.toml metadata."""
from __future__ import annotations
import re
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

_NAME = re.compile(r'^\s*([A-Za-z0-9][A-Za-z0-9_.-]*)(?:\s*\[[^\]\n]*\])?(?:\s*(?:[<>=!~;]|@\s*\S|$))')
_SEPARATOR = re.compile(r'[-_.]+')


def _names(values: object) -> list[str]:
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise ValueError('PEP 621 dependencies must be arrays of strings')
    names: set[str] = set()
    for value in values:
        match = _NAME.match(value)
        if match is None:
            raise ValueError('invalid PEP 621 dependency declaration')
        names.add(_SEPARATOR.sub('-', match.group(1)).lower())
    return sorted(names)


def parse_pyproject_dependencies(content: str) -> dict[str, list[str]]:
    """Exclude build-system requirements and never report versions or credentials."""
    project = tomllib.loads(content).get('project')
    if project is None:
        return {}
    if not isinstance(project, dict):
        raise ValueError('PEP 621 project must be a table')
    groups: dict[str, list[str]] = {}
    if 'dependencies' in project:
        groups['dependencies'] = _names(project['dependencies'])
    extras = project.get('optional-dependencies', {})
    if not isinstance(extras, dict):
        raise ValueError('PEP 621 optional-dependencies must be a table')
    for name, values in sorted(extras.items()):
        groups[f'optional:{name}'] = _names(values)
    return groups
