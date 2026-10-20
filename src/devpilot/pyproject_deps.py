"""Safely inventory only package names from PEP 621 and PEP 735 metadata."""
from __future__ import annotations
import re
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

_NAME = re.compile(r'^\s*([A-Za-z0-9][A-Za-z0-9_.-]*)(?:\s*\[[^\]\n]*\])?(?:\s*(?:[<>=!~;]|@\s*\S|$))')
_SEPARATOR = re.compile(r'[-_.]+')
_GROUP_NAME = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?\Z')


def _names(values: object) -> list[str]:
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise ValueError('PEP 621 dependencies must be arrays of strings')
    names: set[str] = set()
    for value in values:
        match = _NAME.match(value)
        if match is None:
            raise ValueError('invalid dependency declaration')
        names.add(_SEPARATOR.sub('-', match.group(1)).lower())
    return sorted(names)



def _dependency_groups(raw: object) -> dict[str, list[str]]:
    """Resolve PEP 735 includes, rejecting cycles and ambiguous group names."""
    if not isinstance(raw, dict):
        raise ValueError('dependency-groups must be a table')
    groups: dict[str, list[object]] = {}
    for name, members in raw.items():
        if not isinstance(name, str) or not _GROUP_NAME.fullmatch(name):
            raise ValueError('invalid dependency group name')
        canonical = _SEPARATOR.sub('-', name).lower()
        if canonical in groups:
            raise ValueError('duplicate normalized dependency group names')
        if not isinstance(members, list):
            raise ValueError('dependency group must be an array')
        groups[canonical] = members

    resolved: dict[str, list[str]] = {}
    visiting: set[str] = set()

    def resolve(name: str) -> list[str]:
        if name not in groups:
            raise ValueError('unknown included dependency group')
        if name in visiting:
            raise ValueError('cyclic dependency group include')
        if name in resolved:
            return resolved[name]
        visiting.add(name)
        names: set[str] = set()
        for member in groups[name]:
            if isinstance(member, str):
                names.update(_names([member]))
            elif isinstance(member, dict) and set(member) == {'include-group'}:
                included = member['include-group']
                if not isinstance(included, str) or not _GROUP_NAME.fullmatch(included):
                    raise ValueError('invalid included dependency group')
                names.update(resolve(_SEPARATOR.sub('-', included).lower()))
            else:
                raise ValueError('invalid dependency group entry')
        visiting.remove(name)
        resolved[name] = sorted(names)
        return resolved[name]

    return {f'group:{name}': resolve(name) for name in sorted(groups)}

def parse_pyproject_dependencies(content: str) -> dict[str, list[str]]:
    """Exclude build-system requirements and never report versions or credentials."""
    metadata = tomllib.loads(content)
    project = metadata.get('project')
    groups: dict[str, list[str]] = {}
    if project is not None:
        if not isinstance(project, dict):
            raise ValueError('PEP 621 project must be a table')
        if 'dependencies' in project:
            groups['dependencies'] = _names(project['dependencies'])
        extras = project.get('optional-dependencies', {})
        if not isinstance(extras, dict):
            raise ValueError('PEP 621 optional-dependencies must be a table')
        for name, values in sorted(extras.items()):
            groups[f'optional:{name}'] = _names(values)
    if 'dependency-groups' in metadata:
        groups.update(_dependency_groups(metadata['dependency-groups']))
    return groups
