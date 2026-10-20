"""Read-only .NET PackageReference inventory with XML namespace isolation."""

from __future__ import annotations

import xml.etree.ElementTree as ET

_MSBUILD_NS = 'http://schemas.microsoft.com/developer/msbuild/2003'


def parse_dotnet_dependencies(content: str) -> dict[str, list[str]]:
    """Extract NuGet PackageReference names from an MSBuild Project document.

    Modern SDK projects typically have no XML namespace; older projects use
    the MSBuild namespace. Elements from extension namespaces must not be
    mistaken for NuGet references. Package values and versions are omitted.
    """
    upper = content.upper()
    if '<!DOCTYPE' in upper or '<!ENTITY' in upper:
        raise ValueError('DTD and XML entities are not supported')
    root = ET.fromstring(content)
    if root.tag not in ('Project', f'{{{_MSBUILD_NS}}}Project'):
        raise ValueError('.NET manifest root must be an MSBuild Project element')

    prefix = root.tag[:-len('Project')]
    reference_tag = f'{prefix}PackageReference'
    names = set()
    for node in root.iter():
        if node.tag != reference_tag:
            continue
        name = node.attrib.get('Include') or node.attrib.get('Update')
        if name:
            names.add(name)
    return {'PackageReference': sorted(names)}
