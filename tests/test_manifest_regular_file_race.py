"""Regression tests for regular-file replacement while reading manifests."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.manifest import MAX_MANIFEST_BYTES, read_package_json


class ManifestRegularFileRaceTests(unittest.TestCase):
    def test_same_size_regular_file_swap_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / 'package.json'
            replacement = root / 'replacement.json'
            manifest.write_text('{"public": true}')
            replacement.write_text('{"secret": true}')
            original_open = os.open

            def swap_before_open(path, flags):
                os.replace(replacement, manifest)
                return original_open(path, flags)

            with patch('devpilot.manifest.os.open', side_effect=swap_before_open):
                parsed, error = read_package_json(root)
            self.assertIsNone(parsed)
            self.assertEqual(error, 'package.json changed during inspection')

    def test_growth_after_stat_still_has_size_limit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / 'package.json'
            manifest.write_text('{}')
            original_open = os.open

            def grow_before_open(path, flags):
                manifest.write_bytes(b' ' * (MAX_MANIFEST_BYTES + 1))
                return original_open(path, flags)

            with patch('devpilot.manifest.os.open', side_effect=grow_before_open):
                parsed, error = read_package_json(root)
            self.assertIsNone(parsed)
            self.assertIn('inspection limit', error)


if __name__ == '__main__':
    unittest.main()
