"""Only actual .env newlines may create additional variable declarations."""

import tempfile
import unittest
from pathlib import Path

from devpilot.envcheck import inspect_env


class EnvUnicodeLineBoundariesTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_unicode_separators_in_values_cannot_forge_declared_keys(self):
        (self.root / '.env.example').write_text('PRIMARY=example\nSECOND=example\n', encoding='utf-8')
        for separator in ('\u0085', '\u2028', '\u2029', '\v', '\f', '\x1c'):
            with self.subTest(separator=repr(separator)):
                (self.root / '.env').write_text(
                    f'PRIMARY=secret{separator}SECOND=forged\n', encoding='utf-8'
                )
                result = inspect_env(self.root)
                self.assertEqual(result['status'], 'missing_keys')
                self.assertEqual(result['missing_keys'], ['SECOND'])
                self.assertEqual(result['declared_count'], 1)
                self.assertNotIn('secret', str(result))

    def test_unicode_separators_in_template_are_not_new_declarations(self):
        (self.root / '.env.example').write_text('PRIMARY=x\u2028INJECTED=y\n', encoding='utf-8')
        (self.root / '.env').write_text('PRIMARY=real\n', encoding='utf-8')
        result = inspect_env(self.root)
        self.assertEqual(result['status'], 'matched')
        self.assertEqual(result['expected_count'], 1)

    def test_crlf_and_lf_still_separate_declarations(self):
        (self.root / '.env.example').write_bytes(b'FIRST=example\r\nSECOND=example\n')
        (self.root / '.env').write_bytes(b'export FIRST=real\r\nSECOND=real\n')
        result = inspect_env(self.root)
        self.assertEqual(result['status'], 'matched')
        self.assertEqual(result['expected_count'], 2)
        self.assertEqual(result['declared_count'], 2)


if __name__ == '__main__':
    unittest.main()
