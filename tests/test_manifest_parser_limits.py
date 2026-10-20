"""Regression checks for malformed but size-bounded package.json files."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.manifest import read_package_json


class ManifestParserLimitsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / 'package.json'

    def test_nested_json_exceeding_recursion_limit_returns_error(self):
        self.manifest.write_text('{"nested":' + '[' * 15000 + '0' + ']' * 15000 + '}', encoding='utf-8')
        parsed, error = read_package_json(self.root)
        self.assertIsNone(parsed)
        self.assertEqual(error, 'Invalid package.json: JSON exceeds parser limits')

    def test_integer_parser_limit_returns_error(self):
        self.manifest.write_text('{"version": 1}', encoding='utf-8')
        with patch('devpilot.manifest.json.loads', side_effect=ValueError('integer too large')):
            parsed, error = read_package_json(self.root)
        self.assertIsNone(parsed)
        self.assertEqual(error, 'Invalid package.json: JSON exceeds parser limits')

    def test_nonfinite_literals_return_safe_generic_error(self):
        for literal in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(literal=literal):
                self.manifest.write_text('{"secret":"do-not-echo","value":' + literal + '}', encoding='utf-8')
                parsed, error = read_package_json(self.root)
                self.assertIsNone(parsed)
                self.assertEqual(error, 'Invalid package.json: JSON exceeds parser limits')
                self.assertNotIn('do-not-echo', error)

    def test_valid_json_still_works(self):
        self.manifest.write_text('{"scripts":{"test":"echo ok"}}', encoding='utf-8')
        self.assertEqual(read_package_json(self.root)[0]['scripts']['test'], 'echo ok')

    def test_malformed_json_still_returns_diagnostic(self):
        self.manifest.write_text('{oops', encoding='utf-8')
        parsed, error = read_package_json(self.root)
        self.assertIsNone(parsed)
        self.assertIn('Expecting property name', error)

    def test_missing_file_unchanged(self):
        self.assertEqual(read_package_json(self.root), (None, None))


if __name__ == '__main__':
    unittest.main()
