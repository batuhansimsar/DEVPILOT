"""Binary dotenv content must not be mistaken for a complete key inventory."""
import tempfile
import unittest
from pathlib import Path
from devpilot.envcheck import inspect_env


class EnvNULByteTests(unittest.TestCase):
    def test_template_with_nul_is_unreadable_not_matched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.env.example').write_bytes(b'API_TOKEN=secret\x00junk\n')
            (root / '.env').write_bytes(b'API_TOKEN=present\n')
            report = inspect_env(root)
            self.assertEqual(report['status'], 'unreadable_template')
            self.assertEqual(report['detail'], 'contains NUL byte')
            self.assertNotIn('secret', str(report))

    def test_local_with_nul_is_unreadable_not_matched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.env.example').write_bytes(b'API_TOKEN=example\n')
            (root / '.env').write_bytes(b'API_TOKEN=secret\x00suffix\n')
            report = inspect_env(root)
            self.assertEqual(report['status'], 'unreadable_local')
            self.assertEqual(report['detail'], 'contains NUL byte')
            self.assertEqual(report['expected_count'], 1)
            self.assertNotIn('secret', str(report))

    def test_regular_unicode_values_still_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.env.example').write_text('API_TOKEN=example\n', encoding='utf-8')
            (root / '.env').write_text('API_TOKEN=şifre\n', encoding='utf-8')
            self.assertEqual(inspect_env(root)['status'], 'matched')


if __name__ == '__main__':
    unittest.main()
