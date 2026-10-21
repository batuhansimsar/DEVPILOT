"""Multiline dotenv escapes must not forge new key declarations."""

import tempfile
import unittest
from pathlib import Path

from devpilot.envcheck import _keys, inspect_env


class EnvMultilineEscapesTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def write(self, name, content):
        (self.root / name).write_text(content, encoding='utf-8')

    def test_backslash_at_line_end_escapes_next_lines_quote(self):
        self.write('.env', 'BANNER="first\\\n"quoted text\nFORGED=hidden\nlast"\nREAL=yes\n')
        self.assertEqual(_keys(self.root / '.env'), ({'BANNER', 'REAL'}, None))

    def test_even_number_of_backslashes_does_not_escape_next_quote(self):
        self.write('.env', 'BANNER="first\\\\\n"\nREAL=yes\n')
        self.assertEqual(_keys(self.root / '.env'), ({'BANNER', 'REAL'}, None))

    def test_crlf_and_single_quotes(self):
        self.write('.env', "BANNER='first\\\r\n'escaped quote\r\nFAKE=no\r\nlast'\r\nREAL=ok\r\n")
        self.assertEqual(_keys(self.root / '.env'), ({'BANNER', 'REAL'}, None))

    def test_missing_keys_cannot_be_forged_inside_quoted_local_value(self):
        self.write('.env.example', 'REQUIRED=example\n')
        self.write('.env', 'BANNER="first\\\n"escaped\nREQUIRED=forged\nend"\n')
        report = inspect_env(self.root)
        self.assertEqual(report['status'], 'missing_keys')
        self.assertEqual(report['missing_keys'], ['REQUIRED'])
        self.assertEqual(report['declared_count'], 1)
        self.assertNotIn('forged', repr(report))

    def test_multiline_template_value_cannot_add_false_expected_key(self):
        self.write('.env.example', 'BANNER="first\\\n"escaped\nPHANTOM=x\nend"\nREAL=yes\n')
        self.write('.env', 'BANNER=ok\nREAL=yes\n')
        report = inspect_env(self.root)
        self.assertEqual(report['status'], 'matched')
        self.assertEqual(report['expected_count'], 2)


if __name__ == '__main__':
    unittest.main()
