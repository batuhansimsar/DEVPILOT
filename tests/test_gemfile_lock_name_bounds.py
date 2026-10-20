"""Ensure Gemfile.lock inventory handles untrusted oversized package names."""

import unittest

from devpilot.gemfile_lock import parse_gemfile_lock


class GemfileLockNameBoundTests(unittest.TestCase):
    def test_accepts_boundary_and_normalizes_names(self):
        longest = 'A' + 'b' * 213
        lock = f'GEM\n  specs:\n    {longest} (1.0.0)\n    My_Gem (2.0.0)\n'
        self.assertEqual(parse_gemfile_lock(lock), sorted(['my-gem', longest.lower()]))

    def test_skips_oversized_name_without_disclosing_source(self):
        overly_long = 'SecretToken' + 'x' * 205
        lock = ('GIT\n  remote: https://user:secret@example.invalid/\n'
                f'  specs:\n    {overly_long} (2.0.0)\n    valid (1.0.0)\n')
        result = parse_gemfile_lock(lock)
        self.assertEqual(result, ['valid'])
        self.assertNotIn('SecretToken', str(result))
        self.assertNotIn('secret', str(result))
        self.assertNotIn('example.invalid', str(result))

    def test_oversized_nested_constraint_is_not_reported(self):
        lock = 'GEM\n  specs:\n    tiny (1.0)\n      ' + 'a' * 500 + ' (~> 1.0)\n'
        self.assertEqual(parse_gemfile_lock(lock), ['tiny'])


if __name__ == '__main__':
    unittest.main()
