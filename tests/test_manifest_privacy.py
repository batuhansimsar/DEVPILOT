"""Regression coverage for sensitive content in malformed manifests."""

import tempfile
import unittest
from pathlib import Path

from devpilot.manifest import read_package_json


class ManifestPrivacyTests(unittest.TestCase):
    def test_invalid_utf8_does_not_echo_manifest_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = Path(temp) / 'package.json'
            manifest.write_bytes(b'{"credential":"SECRET\xff"}')
            data, error = read_package_json(Path(temp))
        self.assertIsNone(data)
        self.assertEqual(error, 'Invalid package.json: must be UTF-8')
        self.assertNotIn('SECRET', error)

    def test_other_invalid_json_still_has_useful_error(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / 'package.json').write_text('{broken', encoding='utf-8')
            data, error = read_package_json(Path(temp))
        self.assertIsNone(data)
        self.assertIn('Invalid package.json', error)

    def test_valid_package_still_parses(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / 'package.json').write_text('{"scripts":{"test":"node test.js"}}', encoding='utf-8')
            data, error = read_package_json(Path(temp))
        self.assertIsNone(error)
        self.assertEqual(data['scripts']['test'], 'node test.js')


if __name__ == '__main__':
    unittest.main()
