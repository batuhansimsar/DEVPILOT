"""Direct uv.lock parser calls must honor resource and privacy limits."""

import unittest

from devpilot.uv_lock import MAX_UV_LOCK_INPUT_CHARS, MAX_UV_LOCK_PACKAGES, parse_uv_lock


class UvLockInputBoundsTests(unittest.TestCase):
    def test_rejects_oversized_input_before_toml_parsing(self):
        # Even a syntactically invalid oversized input must fail with a fixed,
        # non-sensitive error instead of the TOML parser's diagnostic.
        sensitive_input = 'https://user:secret@example.invalid/' + 'x' * MAX_UV_LOCK_INPUT_CHARS
        with self.assertRaisesRegex(ValueError, 'uv.lock input exceeds safe size limit') as raised:
            parse_uv_lock(sensitive_input)
        self.assertNotIn('secret', str(raised.exception))

    def test_rejects_nonstrings_with_sanitized_error(self):
        for value in (None, 123, b'[[package]]\nname="foo"', {'secret': 'hidden'}):
            with self.subTest(kind=type(value).__name__), self.assertRaisesRegex(
                ValueError, 'uv.lock input exceeds safe size limit'
            ) as raised:
                parse_uv_lock(value)
            self.assertNotIn('secret', str(raised.exception))

    def test_rejects_oversized_package_array(self):
        # Avoid large TOML allocations: use a lightweight fake parser to verify
        # that the package count is validated before per-package processing.
        from unittest.mock import patch

        with patch('devpilot.uv_lock.tomllib.loads', return_value={'package': [None] * (MAX_UV_LOCK_PACKAGES + 1)}):
            with self.assertRaisesRegex(ValueError, 'bounded array'):
                parse_uv_lock('version = 1\n')

    def test_small_valid_input_still_normalizes(self):
        self.assertEqual(parse_uv_lock('[[package]]\nname="My_Pkg"\n'), ['my-pkg'])
        self.assertEqual(parse_uv_lock('\ufeffversion = 1\n'), [])


if __name__ == '__main__':
    unittest.main()
