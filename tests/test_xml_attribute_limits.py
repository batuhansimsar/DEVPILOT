"""Untrusted XML manifests must not exhaust memory via wide attribute lists."""

import unittest

from devpilot.xml_safety import (
    MAX_XML_ATTRIBUTES,
    MAX_XML_ATTRIBUTES_PER_ELEMENT,
    parse_xml_without_doctype,
)


class XMLAttributeLimitTests(unittest.TestCase):
    @staticmethod
    def attributed_node(count: int) -> str:
        attributes = ''.join(f' a{i}="v"' for i in range(count))
        return f'<node{attributes}/>'

    def test_per_element_boundary_is_accepted(self):
        root = parse_xml_without_doctype(
            self.attributed_node(MAX_XML_ATTRIBUTES_PER_ELEMENT)
        )
        self.assertEqual(len(root.attrib), MAX_XML_ATTRIBUTES_PER_ELEMENT)

    def test_rejects_wide_element_without_echoing_private_attribute(self):
        xml = self.attributed_node(MAX_XML_ATTRIBUTES_PER_ELEMENT)[:-2] + ' secret_token="private-data"/>'
        with self.assertRaisesRegex(
            ValueError, rf'^XML attribute count per element exceeds {MAX_XML_ATTRIBUTES_PER_ELEMENT}$'
        ) as caught:
            parse_xml_without_doctype(xml)
        self.assertNotIn('private-data', str(caught.exception))

    def test_total_attribute_boundary_and_overflow(self):
        attributes_per_child = 100
        child = self.attributed_node(attributes_per_child)
        root_at_limit = '<root>' + child * (MAX_XML_ATTRIBUTES // attributes_per_child) + '</root>'
        result = parse_xml_without_doctype(root_at_limit)
        self.assertEqual(len(result), MAX_XML_ATTRIBUTES // attributes_per_child)
        overflow = '<root>' + child * ((MAX_XML_ATTRIBUTES // attributes_per_child) + 1) + '</root>'
        with self.assertRaisesRegex(
            ValueError, rf'^XML total attribute count exceeds {MAX_XML_ATTRIBUTES}$'
        ):
            parse_xml_without_doctype(overflow)

    def test_attributes_do_not_count_text_comments_or_cdata(self):
        root = parse_xml_without_doctype(
            '<root x="1"><!-- a="b" --><![CDATA[x="y"]]><child y="2"/></root>'
        )
        self.assertEqual(root.attrib, {'x': '1'})
        self.assertEqual(root[0].attrib, {'y': '2'})


if __name__ == '__main__':
    unittest.main()
