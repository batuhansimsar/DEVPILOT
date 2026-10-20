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
    r"\s*([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)(?=\s|\[|\(|[<>=!~;@]|$)"
)
_SEPARATORS = re.compile(r"[-_.]+")

_EXTRA_NAME = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
_EXTRAS = re.compile(r"\[\s*" + _EXTRA_NAME + r"(?:\s*,\s*" + _EXTRA_NAME + r")*\s*\]")
_VERSION_PART = r"(?:===|~=|==|!=|<=|>=|<|>)\s*[^\s,;()]+"
_VERSION_LIST = _VERSION_PART + r"(?:\s*,\s*" + _VERSION_PART + r")*"
_VERSIONS = re.compile(r"(?:\(\s*" + _VERSION_LIST + r"\s*\)|" + _VERSION_LIST + r")\Z")


def _valid_requirement_suffix(suffix: str) -> bool:
    """Reject malformed tails instead of silently accepting a package-name prefix.

    This checks the declaration structure without exposing versions, URLs or
    markers to callers. It deliberately does not resolve or execute requirements.
    """
    suffix = suffix.strip()
    if suffix.startswith('['):
        extras = _EXTRAS.match(suffix)
        if extras is None:
            return False
        suffix = suffix[extras.end():].strip()
    if not suffix:
        return True
    if suffix.startswith('@'):
        # An unescaped semicolon can belong to the URL path. A marker after
        # a direct reference is separated by whitespace before the semicolon.
        parts = re.split(r'\s+;', suffix[1:].strip(), maxsplit=1)
        return (bool(parts[0]) and not any(char.isspace() for char in parts[0])
                and (len(parts) == 1 or bool(parts[1].strip())))
    version, marker_sep, marker = suffix.partition(';')
    if marker_sep and not marker.strip():
        return False
    if not version.strip():
        return bool(marker_sep and marker.strip())
    return _VERSIONS.fullmatch(version.strip()) is not None


def _canonical(name: str) -> str:
    return _SEPARATORS.sub("-", name).lower()


def _group_key(name: object) -> str:
    """PEP 735 group names are compared using normalized package-name rules."""
    if not isinstance(name, str) or not _NAME.fullmatch(name):
        raise ValueError('pyproject.toml dependency-groups contain an invalid group name')
    return _canonical(name)


def _requirements(entries: object, label: str) -> set[str]:
    """Only return valid names, never a potentially credential-bearing value."""
    if not isinstance(entries, list):
        raise ValueError(f"pyproject.toml {label} must be a list")
    found: set[str] = set()
    for entry in entries:
        if not isinstance(entry, str):
            raise ValueError(f"pyproject.toml {label} contains an invalid requirement")
        match = _REQUIREMENT.match(entry)
        if not match or not _valid_requirement_suffix(entry[match.end():]):
            raise ValueError(f"pyproject.toml {label} contains an invalid requirement")
        suffix = entry[match.end():].strip()
        if (suffix and suffix[0] not in '[(@<>=!~;'
                or suffix in ('@', ';', '[', '(')):
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
        # Untrusted TOML table keys become report labels; validate every
        # optional/extra group before emitting it to JSON or terminals.
        if label.startswith(("optional:", "group:")) and not _NAME.fullmatch(label.split(":", 1)[1]):
            raise ValueError("pyproject.toml contains an invalid dependency group name")
        found.setdefault(label, set()).update(values)

    if 'project' in data:
        project = _mapping(data['project'], 'project')
        if 'dependencies' in project:
            collect('dependencies', _requirements(project['dependencies'], 'project.dependencies'))
        if 'optional-dependencies' in project:
            optional = _mapping(project['optional-dependencies'], 'project.optional-dependencies')
            normalized_extras: set[str] = set()
            for group, values in optional.items():
                if not _NAME.fullmatch(group):
                    raise ValueError('pyproject.toml contains an invalid optional dependency group name')
                normalized = _canonical(group)
                if normalized in normalized_extras:
                    raise ValueError('pyproject.toml contains duplicate normalized optional dependency groups')
                normalized_extras.add(normalized)
                collect(f'optional:{normalized}', _requirements(values, 'project.optional-dependencies'))

    if 'dependency-groups' in data:
        original_groups = _mapping(data['dependency-groups'], 'dependency-groups')
        # PEP 735 compares group names by normalized spelling, but reports
        # should retain the author's original spelling for readability.
        groups: dict[str, list] = {}
        for name, entries in original_groups.items():
            if not _NAME.fullmatch(name):
                raise ValueError('pyproject.toml contains an invalid dependency group name')
            canonical = _canonical(name)
            if canonical in groups:
                raise ValueError('pyproject.toml contains a duplicate normalized dependency group')
            groups[canonical] = entries

        # Iterative DFS handles deeply nested group includes without Python's
        # recursion limit, while keeping cycles and unknown references errors.
        resolved: dict[str, set[str]] = {}
        visiting: set[str] = set()
        for start in groups:
            pending = [(start, False)]
            while pending:
                current, finish = pending.pop()
                if current in resolved:
                    continue
                if finish:
                    names: set[str] = set()
                    for entry in groups[current]:
                        if isinstance(entry, str):
                            names.update(_requirements([entry], 'dependency-groups'))
                        else:
                            names.update(resolved[_canonical(entry['include-group'])])
                    resolved[current] = names
                    visiting.remove(current)
                    continue
                if current in visiting:
                    raise ValueError('pyproject.toml dependency-groups contain an inclusion cycle')
                visiting.add(current)
                pending.append((current, True))
                entries = groups[current]
                if not isinstance(entries, list):
                    raise ValueError('pyproject.toml dependency-groups must contain lists')
                for entry in reversed(entries):
                    if isinstance(entry, str):
                        _requirements([entry], 'dependency-groups')
                        continue
                    if (not isinstance(entry, dict) or set(entry) != {'include-group'}
                            or not isinstance(entry['include-group'], str)):
                        raise ValueError('pyproject.toml dependency-groups contain an invalid include')
                    reference = _canonical(entry['include-group'])
                    if reference not in groups:
                        raise ValueError('pyproject.toml dependency-groups reference an unknown group')
                    if reference in visiting:
                        raise ValueError('pyproject.toml dependency-groups contain an inclusion cycle')
                    if reference not in resolved:
                        pending.append((reference, False))

        for name in original_groups:
            collect(f'group:{name}', resolved[_canonical(name)])

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
