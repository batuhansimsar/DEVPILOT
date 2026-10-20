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

    def visit(node: ET.Element, in_item_group: bool = False) -> None:
        for child in node:
            # Ignore foreign namespaces and their full subtrees. An extension
            # wrapper must not turn nested elements into MSBuild declarations.
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
                visit(child, item_scope)

    visit(root)
    return {'PackageReference': sorted(names)}
