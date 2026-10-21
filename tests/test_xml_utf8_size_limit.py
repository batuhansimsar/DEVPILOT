"""Regression coverage for Unicode-aware XML input limits."""

import unittest
from unittest.mock import patch

from devpilot.xml_safety import MAX_XML_INPUT_LENGTH, parse_xml_without_doctype


class XMLUTF8SizeLimitTests(unittest.TestCase):
    def test_multibyte_input_exceeding_byte_limit_is_rejected_before_parse(self):
        # The Unicode character count fits, while its UTF-8 byte count does not.
        xml = '<root>' + ('🚀' * (MAX_XML_INPUT_LENGTH // 4)) + '</root>'
        self.assertLess(len(xml), MAX_XML_INPUT_LENGTH)
        with patch('devpilot.xml_safety.ET.fromstring') as parser:
            with self.assertRaisesRegex(ValueError, 'XML input exceeds'):
                parse_xml_without_doctype(xml)
            parser.assert_not_called()

    def test_multibyte_input_at_exact_byte_limit_is_allowed(self):
        body = 'é' * ((MAX_XML_INPUT_LENGTH - len('<root></root>')) // 2) + 'a'
        xml = '<root>' + body + '</root>'
        self.assertEqual(len(xml.encode('utf-8')), MAX_XML_INPUT_LENGTH)
        root = parse_xml_without_doctype(xml)
        self.assertEqual(root.tag, 'root')
        self.assertEqual(root.text, body)

    def test_invalid_unicode_does_not_leak_surrounding_xml(self):
        private_value = 'private-manifest-value'
        xml = '<root>' + private_value + '\ud800</root>'
        with self.assertRaisesRegex(ValueError, 'valid Unicode') as error:
            parse_xml_without_doctype(xml)
        self.assertNotIn(private_value, str(error.exception))

    def test_non_string_inputs_rejected_without_parsing(self):
        for data in (b'<root/>', None, 5):
            with self.subTest(data=data):
                with self.assertRaisesRegex(ValueError, 'must be a string'):
                    parse_xml_without_doctype(data)


if __name__ == '__main__':
    unittest.main()
