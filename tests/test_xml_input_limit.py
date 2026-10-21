"""A giant XML text node must not bypass bounded manifest parsing."""

import unittest

from devpilot.xml_safety import MAX_XML_INPUT_LENGTH, parse_xml_without_doctype


class XMLInputLengthTests(unittest.TestCase):
    def test_giant_text_node_is_rejected_before_parsing(self):
        xml = '<root>' + ('x' * MAX_XML_INPUT_LENGTH) + '</root>'
        with self.assertRaisesRegex(ValueError, 'XML input exceeds'):
            parse_xml_without_doctype(xml)

    def test_giant_comment_is_rejected_before_parsing(self):
        xml = '<root><!--' + ('x' * MAX_XML_INPUT_LENGTH) + '--></root>'
        with self.assertRaisesRegex(ValueError, 'XML input exceeds'):
            parse_xml_without_doctype(xml)

    def test_small_xml_still_parses(self):
        self.assertEqual(parse_xml_without_doctype('<root><child/></root>').tag, 'root')

    def test_doctype_is_still_rejected(self):
        with self.assertRaisesRegex(ValueError, 'DTD'):
            parse_xml_without_doctype('<!DOCTYPE root [<!ENTITY a "b">]><root>&a;</root>')


if __name__ == '__main__':
    unittest.main()
