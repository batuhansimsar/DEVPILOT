"""UTF-8 BOM compatibility for direct uv.lock parser consumers."""

import unittest

from devpilot.uv_lock import parse_uv_lock


class UVLockBOMTests(unittest.TestCase):
    def test_leading_bom_is_accepted(self):
        content = '\ufeffversion = 1\n[[package]]\nname = "HTTPX"\n'
        self.assertEqual(parse_uv_lock(content), ['httpx'])

    def test_bom_only_input_means_no_locked_packages(self):
        self.assertEqual(parse_uv_lock('\ufeff'), [])

    def test_mid_document_bom_is_still_rejected(self):
        content = 'version = 1\n\ufeff[[package]]\nname = "httpx"\n'
        with self.assertRaisesRegex(ValueError, 'invalid uv.lock TOML'):
            parse_uv_lock(content)


if __name__ == '__main__':
    unittest.main()
