"""Parse XML manifests without allowing DTD declarations or entity definitions.

Unlike substring checks, the XML parser distinguishes declarations from harmless
text in comments and CDATA. No external files or network resources are read.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET


MAX_XML_DEPTH = 128
# Wide XML documents can exhaust memory without ever reaching the depth limit.
# Count elements as they are opened so oversized manifests fail during parsing.
MAX_XML_ELEMENTS = 100_000


class _NoDoctypeTreeBuilder(ET.TreeBuilder):
    """Reject DTDs and XML structures that could exhaust downstream consumers."""

    def __init__(self) -> None:
        super().__init__()
        self._depth = 0
        self._elements = 0

    def doctype(self, name: str, pubid: str | None, system: str | None) -> None:
        raise ValueError('DTD and XML entities are not supported')

    def start(self, tag: str, attrs: dict[str, str]) -> ET.Element:
        if self._depth >= MAX_XML_DEPTH:
            raise ValueError(f'XML nesting exceeds {MAX_XML_DEPTH} levels')
        if self._elements >= MAX_XML_ELEMENTS:
            raise ValueError(f'XML element count exceeds {MAX_XML_ELEMENTS}')
        element = super().start(tag, attrs)
        self._depth += 1
        self._elements += 1
        return element

    def end(self, tag: str) -> ET.Element:
        element = super().end(tag)
        self._depth -= 1
        return element


def parse_xml_without_doctype(content: str) -> ET.Element:
    """Return an XML root while refusing DTDs and oversized XML trees."""
    parser = ET.XMLParser(target=_NoDoctypeTreeBuilder())
    return ET.fromstring(content, parser=parser)
