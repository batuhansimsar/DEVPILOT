"""Unicode formatting separators in .env values must not invent key declarations."""

import tempfile
import unittest
from pathlib import Path

from devpilot.envcheck import _keys, inspect_env


class EnvUnicodeLineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, name: str, text: str) -> None:
        (self.root / name).write_bytes(text.encode('utf-8'))

    def test_unicode_separator_in_local_value_does_not_mask_missing_key(self):
        self.write('.env.example', 'REQUIRED=sample\n')
        self.write('.env', 'COMMENT=private\u2028REQUIRED=pretend\n')
        report = inspect_env(self.root)
        self.assertEqual(report['status'], 'missing_keys')
        self.assertEqual(report['missing_keys'], ['REQUIRED'])
        self.assertEqual(report['declared_count'], 1)
        self.assertNotIn('private', str(report))

    def test_unicode_separator_in_template_value_is_not_another_key(self):
        self.write('.env.example', 'TOKEN=value\x85PHANTOM=not-a-key\nEXPECTED=value\n')
        self.write('.env', 'TOKEN=actual\nEXPECTED=actual\n')
        report = inspect_env(self.root)
        self.assertEqual(report['status'], 'matched')
        self.assertEqual(report['expected_count'], 2)

    def test_unicode_whitespace_cannot_prefix_or_pad_a_key(self):
        self.write('.env', '\u2028SPOOF=secret\nTOKEN\u2029 =secret\nexport\u0085ALSO_SPOOF=secret\n')
        self.assertEqual(_keys(self.root / '.env'), (set(), None))

    def test_real_cr_lf_and_crlf_keep_working(self):
        self.write('.env', 'export TOKEN=sample\rSECOND=value\r\n  THIRD = yes\nexport\tFOURTH=x\n')
        self.assertEqual(_keys(self.root / '.env'), ({'TOKEN', 'SECOND', 'THIRD', 'FOURTH'}, None))


if __name__ == '__main__':
    unittest.main()
