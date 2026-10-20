"""Read-only Maven POM dependency inventory with no external XML resolution."""

from __future__ import annotations

import xml.etree.ElementTree as ET


def _local_name(tag: str) -> str:
    return tag.rsplit('}', 1)[-1]


def parse_maven_dependencies(content: str) -> dict[str, list[str]]:
    """List direct project dependencies without versions or managed/plugin entries.

    Maven's dependencyManagement declares versions rather than dependencies;
    plugin dependencies run in a different classpath. Both are intentionally
    excluded to avoid falsely reporting them as project dependencies.
    """
    upper = content.upper()
    if '<!DOCTYPE' in upper or '<!ENTITY' in upper:
        raise ValueError('DTD and XML entities are not supported')
    root = ET.fromstring(content)
    if _local_name(root.tag) != 'project':
        raise ValueError('pom.xml root must be a project element')

    names: set[str] = set()
    for children in root:
        if _local_name(children.tag) != 'dependencies':
            continue
        for dependency in children:
            if _local_name(dependency.tag) != 'dependency':
                continue
            coordinates = {
                _local_name(field.tag): (field.text or '').strip()
                for field in dependency
            }
            group = coordinates.get('groupId')
            artifact = coordinates.get('artifactId')
            if group and artifact:
                names.add(f'{group}:{artifact}')
    return {'dependencies': sorted(names)}
