"""Regression tests for bounded, non-following manifest inspection."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.manifest import MAX_MANIFEST_BYTES, read_package_json


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / 'package.json'

    def test_missing_manifest(self):
        self.assertEqual(read_package_json(self.root), (None, None))

    def test_valid_manifest(self):
        self.manifest.write_text('{"scripts": {"test": "node test.js"}}', encoding='utf-8')
        parsed, error = read_package_json(self.root)
        self.assertIsNone(error)
        self.assertEqual(parsed['scripts']['test'], 'node test.js')

    def test_malformed_and_non_object_json(self):
        self.manifest.write_text('{bad', encoding='utf-8')
        self.assertIn('Invalid package.json', read_package_json(self.root)[1])
        self.manifest.write_text('[]', encoding='utf-8')
        self.assertIn('JSON object', read_package_json(self.root)[1])

    def test_reject_oversized_manifest(self):
        self.manifest.write_bytes(b' ' * (MAX_MANIFEST_BYTES + 1))
        self.assertIn('inspection limit', read_package_json(self.root)[1])

    def test_reject_file_growth_after_stat(self):
        self.manifest.write_text('{}', encoding='utf-8')
        original_open = os.open

        def grow_before_open(path, flags):
            self.manifest.write_bytes(b' ' * (MAX_MANIFEST_BYTES + 1))
            return original_open(path, flags)

        with patch('devpilot.manifest.os.open', side_effect=grow_before_open):
            _, error = read_package_json(self.root)
        self.assertIn('inspection limit', error)

    def test_ignore_symlink_without_reading_target(self):
        with tempfile.TemporaryDirectory() as private:
            target = Path(private) / 'private.json'
            target.write_text('{"private": true}', encoding='utf-8')
            try:
                self.manifest.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlink creation not supported')
            self.assertEqual(read_package_json(self.root), (None, None))

    @unittest.skipUnless(hasattr(os, 'O_NOFOLLOW'), 'platform lacks O_NOFOLLOW')
    def test_refuse_symlink_swapped_after_stat(self):
        self.manifest.write_text('{}', encoding='utf-8')
        target = self.root / 'secret.json'
        target.write_text('{"secret": true}', encoding='utf-8')
        original_open = os.open

        def swap_before_open(path, flags):
            self.manifest.unlink()
            self.manifest.symlink_to(target)
            return original_open(path, flags)

        with patch('devpilot.manifest.os.open', side_effect=swap_before_open):
            parsed, error = read_package_json(self.root)
        self.assertIsNone(parsed)
        self.assertIn('Invalid package.json', error)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'platform lacks FIFO support')
    def test_ignore_fifo_without_blocking(self):
        os.mkfifo(self.manifest)
        self.assertEqual(read_package_json(self.root), (None, None))


if __name__ == '__main__':
    unittest.main()
