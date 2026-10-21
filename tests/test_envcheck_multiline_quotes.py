"""Multiline dotenv values must not be mistaken for key declarations."""

import tempfile
import unittest
from pathlib import Path

from devpilot.envcheck import _keys, inspect_env


class EnvMultilineQuoteTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def write(self, name: str, content: str) -> None:
        (self.root / name).write_text(content, encoding='utf-8')

    def test_local_quoted_value_cannot_forge_required_key(self):
        self.write('.env.example', 'REQUIRED=example\n')
        self.write('.env', 'BANNER="hello\nREQUIRED=forged\nworld"\n')
        report = inspect_env(self.root)
        self.assertEqual(report['status'], 'missing_keys')
        self.assertEqual(report['missing_keys'], ['REQUIRED'])
        self.assertEqual(report['declared_count'], 1)
        self.assertNotIn('forged', repr(report))

    def test_template_quoted_value_cannot_invent_requirement(self):
        self.write('.env.example', "BANNER='line one\nPHANTOM=forged\nline three'\nREAL=x\n")
        self.write('.env', 'BANNER=real\nREAL=real\n')
        report = inspect_env(self.root)
        self.assertEqual(report['status'], 'matched')
        self.assertEqual(report['expected_count'], 2)

    def test_escaped_quotes_and_real_declarations(self):
        self.write('.env', 'FIRST="line \\" not closed\nFORGED=no\nend"\nREAL=yes\n')
        self.assertEqual(_keys(self.root / '.env'), ({'FIRST', 'REAL'}, None))

    def test_unclosed_quote_does_not_accept_following_pseudo_keys(self):
        self.write('.env', 'MESSAGE="never finished\nFALSE_KEY=inside value\n')
        self.assertEqual(_keys(self.root / '.env'), ({'MESSAGE'}, None))

    def test_single_line_quote_allows_following_declarations(self):
        self.write('.env', 'ONE="finished"\nTWO=real\n')
        self.assertEqual(_keys(self.root / '.env'), ({'ONE', 'TWO'}, None))


if __name__ == '__main__':
    unittest.main()
