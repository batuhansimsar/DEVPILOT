"""Gem specs must remain scoped to the actual `specs:` subsection."""

import unittest

from devpilot.gemfile_lock import parse_gemfile_lock


class GemfileLockSectionTests(unittest.TestCase):
    def test_other_source_metadata_cannot_impersonate_spec_entries(self):
        lock = ('GEM\n'
                '  remote: https://example.test\n'
                '  specs:\n'
                '    actual-gem (1.0)\n'
                '  other: metadata\n'
                '    phantom-gem (2.0)\n'
                '  specs:\n'
                '    resumed-gem (3.0)\n'
                '      nested-dep (~> 1.0)\n'
                'DEPENDENCIES\n'
                '  actual-gem\n')
        self.assertEqual(parse_gemfile_lock(lock), ['actual-gem', 'resumed-gem'])

    def test_deeply_indented_specs_marker_is_not_a_source_section(self):
        lock = ('GIT\n'
                '  remote: https://example.test\n'
                '    specs:\n'
                '    not-a-spec (1.0)\n'
                '  specs:\n'
                '    real-spec (2.0)\n')
        self.assertEqual(parse_gemfile_lock(lock), ['real-spec'])


if __name__ == '__main__':
    unittest.main()
