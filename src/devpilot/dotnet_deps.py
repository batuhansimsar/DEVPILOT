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
    item_group_tag = f'{prefix}ItemGroup'
    reference_tag = f'{prefix}PackageReference'
    names: set[str] = set()

    # An explicit stack handles deeply nested but valid project XML without
    # depending on Python's recursion limit.
    stack: list[tuple[ET.Element, bool]] = [(root, False)]
    while stack:
        node, in_item_group = stack.pop()
        for child in node:
            # Ignore foreign namespace subtrees, not just their leaf tags.
            if prefix:
                if not child.tag.startswith(prefix):
                    continue
            elif child.tag.startswith('{'):
                continue

            item_scope = in_item_group or child.tag == item_group_tag
            if child.tag == reference_tag and item_scope:
                name = child.attrib.get('Include') or child.attrib.get('Update')
                if name:
                    names.add(name)
            else:
                stack.append((child, item_scope))

    return {'PackageReference': sorted(names)}
