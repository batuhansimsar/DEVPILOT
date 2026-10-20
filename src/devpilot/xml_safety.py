"""Parse XML manifests without allowing DTD declarations or entity definitions.

Unlike substring checks, the XML parser distinguishes declarations from harmless
text in comments and CDATA. No external files or network resources are read.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET


class _NoDoctypeTreeBuilder(ET.TreeBuilder):
    """Reject DTDs before their entity declarations can be processed."""

    def doctype(self, name: str, pubid: str | None, system: str | None) -> None:
        raise ValueError('DTD and XML entities are not supported')


def parse_xml_without_doctype(content: str) -> ET.Element:
    """Return an XML document root while refusing any real DOCTYPE declaration."""
    parser = ET.XMLParser(target=_NoDoctypeTreeBuilder())
    return ET.fromstring(content, parser=parser)
