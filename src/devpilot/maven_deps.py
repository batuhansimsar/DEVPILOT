"""Read-only Maven POM dependency inventory with no external XML resolution."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .xml_safety import parse_xml_without_doctype

_MAVEN_NS = 'http://maven.apache.org/POM/4.0.0'
# A dependency inventory reports *identifiers* only. Invalid coordinates may
# contain terminal control sequences, URLs or credentials from untrusted POMs.
# Leave unresolved Maven property references out of reports rather than
# repeating arbitrary values that happen to appear in an XML element.
_COORDINATE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*\Z')


def _local_name(tag: str) -> str:
    return tag.rsplit('}', 1)[-1]


def parse_maven_dependencies(content: str) -> dict[str, list[str]]:
    """List direct and conditional profile dependencies, without versions.

    Maven's dependencyManagement declares versions rather than dependencies;
    plugin dependencies run in a different classpath. Both are excluded.
    Profile dependencies are reported separately because activation is unknown.
    Extension namespaces cannot contribute Maven dependency declarations.
    """
    root = parse_xml_without_doctype(content)
    if root.tag not in ('project', f'{{{_MAVEN_NS}}}project'):
        raise ValueError('pom.xml root must be a Maven project element')

    # A POM can use the Maven default namespace or no namespace at all.
    # Only elements from the project's own namespace are Maven declarations.
    namespace = root.tag.partition('}')[0] + '}' if root.tag.startswith('{') else ''
    dependencies_tag = f'{namespace}dependencies'
    dependency_tag = f'{namespace}dependency'
    group_tag = f'{namespace}groupId'
    artifact_tag = f'{namespace}artifactId'
    profiles_tag = f'{namespace}profiles'
    profile_tag = f'{namespace}profile'

    def collect(container: ET.Element, names: set[str]) -> None:
        for dependency in container:
            if dependency.tag != dependency_tag:
                continue
            coordinates: dict[str, str] = {}
            for field in dependency:
                if field.tag not in (group_tag, artifact_tag):
                    continue
                if field.tag in coordinates:
                    # Duplicate coordinates are ambiguous; never echo values.
                    raise ValueError('pom.xml dependency contains duplicate coordinates')
                # Nested XML must not let a partial value pass as a package ID.
                if len(field):
                    raise ValueError('pom.xml dependency contains an invalid coordinate')
                coordinates[field.tag] = (field.text or '').strip()
            group = coordinates.get(group_tag)
            artifact = coordinates.get(artifact_tag)
            if group and artifact:
                if not _COORDINATE.fullmatch(group) or not _COORDINATE.fullmatch(artifact):
                    raise ValueError('pom.xml dependency contains an invalid coordinate')
                names.add(f'{group}:{artifact}')

    direct: set[str] = set()
    conditional: set[str] = set()
    for child in root:
        if child.tag == dependencies_tag:
            collect(child, direct)
        elif child.tag == profiles_tag:
            for profile in child:
                if profile.tag != profile_tag:
                    continue
                for section in profile:
                    if section.tag == dependencies_tag:
                        collect(section, conditional)

    result = {'dependencies': sorted(direct)}
    if conditional:
        result['profile-dependencies'] = sorted(conditional)
    return result
