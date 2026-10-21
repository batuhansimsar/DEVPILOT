"""Regression tests for invalid UTF-8 in read-only dotenv inspections."""

import tempfile
import unittest
from pathlib import Path

from devpilot.envcheck import inspect_env


class InvalidEncodingTests(unittest.TestCase):
    def test_template_invalid_utf8_is_reported_not_trusted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.env.example').write_bytes(b'TOKEN=secret-value\xff\n')
            result = inspect_env(root)
            self.assertEqual(result, {'template': '.env.example',
                                      'status': 'unreadable_template', 'detail': 'invalid UTF-8'})
            self.assertNotIn('secret', repr(result))

    def test_local_invalid_utf8_is_not_marked_matched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.env.example').write_text('TOKEN=expected\n')
            (root / '.env').write_bytes(b'TOKEN=actual-secret\xff\n')
            result = inspect_env(root)
            self.assertEqual(result, {'template': '.env.example',
                                      'status': 'unreadable_local', 'detail': 'invalid UTF-8',
                                      'expected_count': 1})
            self.assertNotIn('actual-secret', repr(result))

    def test_utf8_bom_and_unicode_values_remain_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.env.example').write_bytes(b'\xef\xbb\xbfTOKEN=caf\xc3\xa9\n')
            (root / '.env').write_text('TOKEN=çalışıyor\n', encoding='utf-8')
            result = inspect_env(root)
            self.assertEqual(result['status'], 'matched')
            self.assertEqual(result['expected_count'], 1)


if __name__ == '__main__':
    unittest.main()
