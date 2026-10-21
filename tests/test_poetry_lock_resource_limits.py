"""Resource budgets and secret-safe errors for direct Poetry lock parsing."""

import unittest
from unittest.mock import patch

from devpilot.poetry_lock import MAX_POETRY_LOCK_INPUT_BYTES, parse_poetry_lock


class PoetryLockResourceLimitsTests(unittest.TestCase):
    def test_rejects_non_string_content(self):
        for content in (None, b'[[package]]', 42, ['[[package]]']):
            with self.subTest(value_type=type(content).__name__):
                with self.assertRaisesRegex(ValueError, 'safe size limit or is invalid'):
                    parse_poetry_lock(content)

    def test_oversized_ascii_input_does_not_reach_parser(self):
        content = '# secret\n' + 'x' * MAX_POETRY_LOCK_INPUT_BYTES
        with patch('devpilot.poetry_lock.tomllib.loads') as loads:
            with self.assertRaisesRegex(ValueError, 'safe size limit') as raised:
                parse_poetry_lock(content)
            loads.assert_not_called()
        self.assertNotIn('secret', str(raised.exception))

    def test_multibyte_input_limited_by_utf8_bytes(self):
        content = '# secret ' + 'é' * (MAX_POETRY_LOCK_INPUT_BYTES // 2)
        self.assertLess(len(content), MAX_POETRY_LOCK_INPUT_BYTES)
        with patch('devpilot.poetry_lock.tomllib.loads') as loads:
            with self.assertRaisesRegex(ValueError, 'safe size limit') as raised:
                parse_poetry_lock(content)
            loads.assert_not_called()
        self.assertNotIn('secret', str(raised.exception))

    def test_rejects_unpaired_surrogate_privately(self):
        with self.assertRaisesRegex(ValueError, 'valid Unicode') as raised:
            parse_poetry_lock('# secret\ud800')
        self.assertNotIn('secret', str(raised.exception))

    def test_boundary_and_bom_are_accepted(self):
        header = '\ufeff[[package]]\nname = "valid_pkg"\n'
        filler = '#' + 'x' * (MAX_POETRY_LOCK_INPUT_BYTES - len(header.encode('utf-8')) - 1)
        content = header + filler
        self.assertEqual(len(content.encode('utf-8')), MAX_POETRY_LOCK_INPUT_BYTES)
        self.assertEqual(parse_poetry_lock(content), ['valid-pkg'])


if __name__ == '__main__':
    unittest.main()
