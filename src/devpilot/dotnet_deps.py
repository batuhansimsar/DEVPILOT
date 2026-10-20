"""Read-only .NET PackageReference inventory with XML namespace isolation."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

_MSBUILD_NS = 'http://schemas.microsoft.com/developer/msbuild/2003'
# Literal NuGet package IDs contain letters, digits, dots, underscores and
# hyphens. A bounded, conservative identifier is safe to echo in reports;
# MSBuild property expressions and arbitrary URLs are not package IDs.
_PACKAGE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}\Z')


def parse_dotnet_dependencies(content: str) -> dict[str, list[str]]:
    """Extract literal NuGet PackageReference names from an MSBuild project.

    Both modern SDK projects and legacy MSBuild-namespace projects are
    supported. Refuse dynamic or malformed names rather than accidentally
    printing project-defined expressions, URLs or credentials in diagnostics.
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
                if name is not None:
                    if not _PACKAGE_ID.fullmatch(name):
                        # Never interpolate untrusted attributes into a warning.
                        raise ValueError('.NET manifest contains an invalid PackageReference identifier')
                    names.add(name)
            else:
                stack.append((child, item_scope))

    return {'PackageReference': sorted(names)}
