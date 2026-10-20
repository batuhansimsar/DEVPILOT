"""Regression tests for ambiguous package.json keys, without leaking key names."""

import tempfile
import unittest
from pathlib import Path

from devpilot.manifest import read_package_json


class PackageDuplicateKeyTests(unittest.TestCase):
    def check_duplicate(self, content: str) -> str:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'package.json').write_text(content, encoding='utf-8')
            parsed, error = read_package_json(Path(directory))
        self.assertIsNone(parsed)
        self.assertIsNotNone(error)
        self.assertIn('duplicate JSON object keys', error)
        return error

    def test_duplicate_top_level_scripts_rejected(self):
        self.check_duplicate('{"scripts":{"test":"safe"},"scripts":{"test":"unsafe"}}')

    def test_duplicate_nested_script_key_rejected(self):
        self.check_duplicate('{"scripts":{"test":"safe","test":"unsafe"}}')

    def test_duplicate_key_name_never_leaks(self):
        error = self.check_duplicate('{"private-token-should-not-appear":1,"private-token-should-not-appear":2}')
        self.assertNotIn('private-token-should-not-appear', error)

    def test_same_key_in_distinct_objects_is_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'package.json').write_text(
                '{"dependencies":{"demo":"1.0"},"devDependencies":{"demo":"2.0"}}',
                encoding='utf-8',
            )
            parsed, error = read_package_json(Path(directory))
        self.assertIsNone(error)
        self.assertEqual(parsed['dependencies']['demo'], '1.0')
        self.assertEqual(parsed['devDependencies']['demo'], '2.0')


if __name__ == '__main__':
    unittest.main()
