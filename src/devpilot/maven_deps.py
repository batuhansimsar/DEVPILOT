"""Read-only Maven POM dependency inventory with no external XML resolution."""

from __future__ import annotations

import xml.etree.ElementTree as ET

_MAVEN_NS = 'http://maven.apache.org/POM/4.0.0'


def _local_name(tag: str) -> str:
    return tag.rsplit('}', 1)[-1]


def parse_maven_dependencies(content: str) -> dict[str, list[str]]:
    """List direct project dependencies without versions or managed/plugin entries.

    Maven's dependencyManagement declares versions rather than dependencies;
    plugin dependencies run in a different classpath. Both are intentionally
    excluded to avoid falsely reporting them as project dependencies.
    Elements from extension namespaces are not Maven dependency declarations.
    """
    upper = content.upper()
    if '<!DOCTYPE' in upper or '<!ENTITY' in upper:
        raise ValueError('DTD and XML entities are not supported')
    root = ET.fromstring(content)
    if root.tag not in ('project', f'{{{_MAVEN_NS}}}project'):
        raise ValueError('pom.xml root must be a Maven project element')

    # A POM can use the Maven default namespace or no namespace at all.
    # Only elements from the project's own namespace are Maven declarations.
    namespace = root.tag.partition('}')[0] + '}' if root.tag.startswith('{') else ''
    dependencies_tag = f'{namespace}dependencies'
    dependency_tag = f'{namespace}dependency'
    group_tag = f'{namespace}groupId'
    artifact_tag = f'{namespace}artifactId'

    names: set[str] = set()
    for children in root:
        if children.tag != dependencies_tag:
            continue
        for dependency in children:
            if dependency.tag != dependency_tag:
                continue
            coordinates: dict[str, str] = {}
            for field in dependency:
                if field.tag not in (group_tag, artifact_tag):
                    continue
                if field.tag in coordinates:
                    # Duplicate coordinates are ambiguous; do not log private values.
                    raise ValueError('pom.xml dependency contains duplicate coordinates')
                coordinates[field.tag] = (field.text or '').strip()
            group = coordinates.get(group_tag)
            artifact = coordinates.get(artifact_tag)
            if group and artifact:
                names.add(f'{group}:{artifact}')
    return {'dependencies': sorted(names)}
