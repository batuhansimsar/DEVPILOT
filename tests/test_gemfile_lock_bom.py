"""BOM handling in Ruby lockfile dependency inventory."""

import unittest

from devpilot.gemfile_lock import parse_gemfile_lock


class GemfileLockBOMTests(unittest.TestCase):
    def test_leading_utf8_bom_preserves_first_source_section(self):
        lock = ('\ufeffGEM\n'
                '  remote: https://user:secret@registry.example.invalid\n'
                '  specs:\n'
                '    My_Gem (1.0)\n'
                '      subdependency (>= 0)\n'
                'GIT\n'
                '  specs:\n'
                '    git-gem (2.0)\n')
        result = parse_gemfile_lock(lock)
        self.assertEqual(result, ['git-gem', 'my-gem'])
        self.assertNotIn('secret', repr(result))

    def test_internal_bom_does_not_start_a_source_section(self):
        lock = ('\ufeffGEM\n'
                '  specs:\n'
                '    valid (1.0)\n'
                'DEPENDENCIES\n'
                '\ufeffGEM\n'
                '  specs:\n'
                '    injected (2.0)\n')
        self.assertEqual(parse_gemfile_lock(lock), ['valid'])


if __name__ == '__main__':
    unittest.main()
