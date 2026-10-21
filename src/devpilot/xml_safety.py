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
# A single node with unusually many attributes consumes memory even when both
# the depth and element count are small. Legitimate build manifests rarely have
# more than a handful of attributes per element.
MAX_XML_ATTRIBUTES_PER_ELEMENT = 1024
# Bound the overall attribute count as well as individual wide elements.
MAX_XML_ATTRIBUTES = 100_000
# Protect direct callers too: even a single text node can consume excessive
# memory without exceeding either the element-count or nesting limit.
MAX_XML_INPUT_LENGTH = 2 * 1024 * 1024


class _NoDoctypeTreeBuilder(ET.TreeBuilder):
    """Reject DTDs and XML structures that could exhaust downstream consumers."""

    def __init__(self) -> None:
        super().__init__()
        self._depth = 0
        self._elements = 0
        self._attributes = 0

    def doctype(self, name: str, pubid: str | None, system: str | None) -> None:
        raise ValueError('DTD and XML entities are not supported')

    def start(self, tag: str, attrs: dict[str, str]) -> ET.Element:
        if self._depth >= MAX_XML_DEPTH:
            raise ValueError(f'XML nesting exceeds {MAX_XML_DEPTH} levels')
        if self._elements >= MAX_XML_ELEMENTS:
            raise ValueError(f'XML element count exceeds {MAX_XML_ELEMENTS}')
        attribute_count = len(attrs)
        if attribute_count > MAX_XML_ATTRIBUTES_PER_ELEMENT:
            raise ValueError(f'XML attribute count per element exceeds {MAX_XML_ATTRIBUTES_PER_ELEMENT}')
        if self._attributes + attribute_count > MAX_XML_ATTRIBUTES:
            raise ValueError(f'XML total attribute count exceeds {MAX_XML_ATTRIBUTES}')
        element = super().start(tag, attrs)
        self._depth += 1
        self._elements += 1
        self._attributes += attribute_count
        return element

    def end(self, tag: str) -> ET.Element:
        element = super().end(tag)
        self._depth -= 1
        return element


def parse_xml_without_doctype(content: str) -> ET.Element:
    """Return an XML root while refusing DTDs and oversized XML trees."""
    if not isinstance(content, str):
        raise ValueError('XML input must be a string')
    # The parser works on UTF-8, not character counts. Multi-byte text could
    # previously exceed the advertised 2 MiB budget without being rejected.
    # Check characters first to avoid encoding obviously oversized inputs.
    if len(content) > MAX_XML_INPUT_LENGTH:
        raise ValueError(f'XML input exceeds {MAX_XML_INPUT_LENGTH} byte limit')
    try:
        encoded_length = len(content.encode('utf-8'))
    except UnicodeEncodeError:
        # Avoid propagating exceptions containing fragments of untrusted XML.
        raise ValueError('XML input must contain valid Unicode') from None
    if encoded_length > MAX_XML_INPUT_LENGTH:
        raise ValueError(f'XML input exceeds {MAX_XML_INPUT_LENGTH} byte limit')
    parser = ET.XMLParser(target=_NoDoctypeTreeBuilder())
    return ET.fromstring(content, parser=parser)
