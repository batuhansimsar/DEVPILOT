"""Direct TOML parser calls must honor the same byte budget as file scans."""

import unittest
from unittest.mock import patch

from devpilot.pylock import MAX_PYLOCK_INPUT_CHARS, parse_pylock
from devpilot.uv_lock import MAX_UV_LOCK_INPUT_CHARS, parse_uv_lock


class TOMLInputLimitsTests(unittest.TestCase):
    def test_multibyte_content_is_rejected_before_toml_parsing(self):
        for parser, limit, module in (
            (parse_pylock, MAX_PYLOCK_INPUT_CHARS, 'devpilot.pylock.tomllib.loads'),
            (parse_uv_lock, MAX_UV_LOCK_INPUT_CHARS, 'devpilot.uv_lock.tomllib.loads'),
        ):
            # Fits the old character cap but exceeds the UTF-8 byte cap.
            content = 'note = "' + ('é' * (limit // 2)) + '"\n'
            self.assertLess(len(content), limit)
            with self.subTest(parser=parser.__name__), patch(module) as loads:
                with self.assertRaisesRegex(ValueError, 'safe size limit') as error:
                    parser(content)
                loads.assert_not_called()
                self.assertNotIn('note', str(error.exception))

    def test_surrogates_are_rejected_without_leaking_source_text(self):
        for parser in (parse_pylock, parse_uv_lock):
            with self.subTest(parser=parser.__name__):
                with self.assertRaisesRegex(ValueError, 'invalid') as error:
                    parser('secret = "\ud800"')
                self.assertIsNone(error.exception.__cause__)
                self.assertNotIn('secret', str(error.exception))

    def test_valid_unicode_metadata_remains_supported(self):
        self.assertEqual(parse_uv_lock('version = 1\nnote = "café"\n'), [])
        self.assertEqual(parse_pylock('lock-version = "1.0"\ncreated-by = "café"\npackages = []\n'), [])


if __name__ == '__main__':
    unittest.main()
