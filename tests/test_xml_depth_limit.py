"""Bound untrusted XML nesting without rejecting ordinary manifest structures."""

import unittest

from devpilot.xml_safety import MAX_XML_DEPTH, parse_xml_without_doctype


class XMLDepthLimitTests(unittest.TestCase):
    @staticmethod
    def nested_xml(depth: int) -> str:
        return '<node>' * depth + '</node>' * depth

    def test_accepts_maximum_depth(self):
        root = parse_xml_without_doctype(self.nested_xml(MAX_XML_DEPTH))
        self.assertEqual(root.tag, 'node')

    def test_rejects_excessive_depth_without_echoing_xml(self):
        payload = self.nested_xml(MAX_XML_DEPTH + 1)
        with self.assertRaisesRegex(ValueError, r'^XML nesting exceeds 128 levels$') as error:
            parse_xml_without_doctype(payload)
        self.assertNotIn('<node>', str(error.exception))

    def test_rejects_dtd_even_under_limit(self):
        with self.assertRaisesRegex(ValueError, 'DTD and XML entities are not supported'):
            parse_xml_without_doctype('<!DOCTYPE node><node/>')

    def test_comments_and_cdata_do_not_count_toward_nesting(self):
        root = parse_xml_without_doctype(
            '<root><!-- <a><b> -->' + '<node>' * (MAX_XML_DEPTH - 1)
            + '<![CDATA[<a><b>]]>' + '</node>' * (MAX_XML_DEPTH - 1) + '</root>'
        )
        self.assertEqual(root.tag, 'root')


if __name__ == '__main__':
    unittest.main()
