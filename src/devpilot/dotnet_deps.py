"""Read-only .NET package inventory with XML namespace isolation.

Also supports central package versions in Directory.Packages.props files.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .xml_safety import parse_xml_without_doctype

_MSBUILD_NS = 'http://schemas.microsoft.com/developer/msbuild/2003'
# Literal NuGet package IDs contain letters, digits, dots, underscores and
# hyphens. A bounded, conservative identifier is safe to echo in reports;
# MSBuild property expressions and arbitrary URLs are not package IDs.
_PACKAGE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,99}\Z')


def parse_dotnet_dependencies(content: str, *, central: bool = False) -> dict[str, list[str]]:
    """Extract literal NuGet package IDs from an MSBuild project or props file.

    ``central=True`` reads PackageVersion entries used by NuGet central package
    management (Directory.Packages.props); otherwise PackageReference entries
    are read. Both modern SDK projects and legacy MSBuild-namespace projects
    are supported. Refuse dynamic or malformed names rather than accidentally
    printing project-defined expressions, URLs or credentials in diagnostics.
    """
    root = parse_xml_without_doctype(content)
    if root.tag not in ('Project', f'{{{_MSBUILD_NS}}}Project'):
        raise ValueError('.NET manifest root must be an MSBuild Project element')

    prefix = root.tag[:-len('Project')]
    item_group_tag = f'{prefix}ItemGroup'
    element = 'PackageVersion' if central else 'PackageReference'
    reference_tag = f'{prefix}{element}'
    # NuGet IDs are case-insensitive; casing aliases must not inflate counts.
    # Keep a deterministic spelling so manifest entry order does not matter.
    names: dict[str, str] = {}

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
                        raise ValueError(f'.NET manifest contains an invalid {element} identifier')
                    normalized = name.casefold()
                    previous = names.get(normalized)
                    if previous is None or name < previous:
                        names[normalized] = name
            else:
                stack.append((child, item_scope))

    return {element: sorted(names.values())}
