"""Do not invent Ruby lockfile records from nonphysical line separators."""

import unittest

from devpilot.gemfile_lock import MAX_GEMFILE_LOCK_CHARS, parse_gemfile_lock


class GemfileLockPhysicalLineTests(unittest.TestCase):
    def test_unicode_and_ascii_control_separators_are_not_physical_lines(self):
        for separator in ('\u2028', '\u2029', '\x85', '\v', '\f'):
            with self.subTest(separator=repr(separator)):
                self.assertEqual(
                    parse_gemfile_lock(f'GEM{separator}  specs:{separator}    phantom (1.0)'),
                    [],
                )

    def test_embedded_separators_cannot_forge_specs_in_remote_metadata(self):
        for separator in ('\u2028', '\x85'):
            with self.subTest(separator=repr(separator)):
                content = f'GEM\n  remote: private{separator}  specs:{separator}    phantom (1.0)\n'
                self.assertEqual(parse_gemfile_lock(content), [])

    def test_valid_cr_lf_and_crlf_lockfiles_remain_supported(self):
        for newline in ('\n', '\r', '\r\n'):
            with self.subTest(newline=repr(newline)):
                content = f'GEM{newline}  specs:{newline}    My_Gem (2.1.0){newline}'
                self.assertEqual(parse_gemfile_lock(content), ['my-gem'])

    def test_direct_input_rejects_oversized_and_nonstring_data(self):
        for value in ('secret-' + 'x' * MAX_GEMFILE_LOCK_CHARS, None, b'GEM\n'):
            with self.subTest(type=type(value).__name__), self.assertRaisesRegex(
                ValueError, 'Gemfile.lock input is invalid or exceeds safe size limit'
            ) as caught:
                parse_gemfile_lock(value)
            self.assertNotIn('secret-', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
