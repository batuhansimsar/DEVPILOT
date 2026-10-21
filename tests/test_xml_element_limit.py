"""Reject wide XML manifests before they exhaust parser memory."""

import unittest
from unittest.mock import patch

from devpilot.xml_safety import MAX_XML_ELEMENTS, parse_xml_without_doctype


class XMLElementLimitTests(unittest.TestCase):
    def test_accepts_exact_element_limit(self):
        with patch('devpilot.xml_safety.MAX_XML_ELEMENTS', 4):
            root = parse_xml_without_doctype('<root><a/><b/><c/></root>')
        self.assertEqual(len(root), 3)

    def test_rejects_wide_tree_and_does_not_echo_input(self):
        payload = '<root><a/><b/><c/><private-api-key/></root>'
        with patch('devpilot.xml_safety.MAX_XML_ELEMENTS', 4):
            with self.assertRaisesRegex(ValueError, r'^XML element count exceeds 4$') as error:
                parse_xml_without_doctype(payload)
        self.assertNotIn('private-api-key', str(error.exception))

    def test_nested_nodes_count_toward_total(self):
        with patch('devpilot.xml_safety.MAX_XML_ELEMENTS', 3):
            with self.assertRaisesRegex(ValueError, 'XML element count exceeds 3'):
                parse_xml_without_doctype('<root><a><b><c/></b></a></root>')

    def test_comments_and_cdata_do_not_count(self):
        with patch('devpilot.xml_safety.MAX_XML_ELEMENTS', 2):
            root = parse_xml_without_doctype('<root><!-- <a/> --><![CDATA[<b/>]]><child/></root>')
        self.assertEqual(len(root), 1)

    def test_real_limit_rejects_oversized_manifest(self):
        payload = '<root>' + '<child/>' * MAX_XML_ELEMENTS + '</root>'
        with self.assertRaisesRegex(ValueError, rf'^XML element count exceeds {MAX_XML_ELEMENTS}$'):
            parse_xml_without_doctype(payload)


if __name__ == '__main__':
    unittest.main()
