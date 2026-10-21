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
        self.assertEqual(_keys(self.root / '.env'), (None, 'unterminated quoted value'))

    def test_single_line_quote_allows_following_declarations(self):
        self.write('.env', 'ONE="finished"\nTWO=real\n')
        self.assertEqual(_keys(self.root / '.env'), ({'ONE', 'TWO'}, None))


    def test_unterminated_template_is_not_reported_as_matched(self):
        self.write('.env.example', 'TOKEN="sensitive value\nFAKE=not-a-key\n')
        self.write('.env', 'TOKEN=present\n')
        report = inspect_env(self.root)
        self.assertEqual(report['status'], 'unreadable_template')
        self.assertEqual(report['detail'], 'unterminated quoted value')
        self.assertNotIn('sensitive value', repr(report))

    def test_unterminated_local_is_not_reported_as_matched(self):
        self.write('.env.example', 'TOKEN=required\n')
        self.write('.env', 'TOKEN="sensitive value\nFAKE=not-a-key\n')
        report = inspect_env(self.root)
        self.assertEqual(report['status'], 'unreadable_local')
        self.assertEqual(report['detail'], 'unterminated quoted value')
        self.assertEqual(report['expected_count'], 1)
        self.assertNotIn('sensitive value', repr(report))

    def test_escaped_final_quote_is_not_a_closing_quote(self):
        self.write('.env', 'TOKEN="value\\"\n')
        self.assertEqual(_keys(self.root / '.env'), (None, 'unterminated quoted value'))


if __name__ == '__main__':
    unittest.main()
