"""Ruby lockfile name extraction tests."""

import unittest

from devpilot.gemfile_lock import parse_gemfile_lock


class GemfileLockTests(unittest.TestCase):
    def test_source_sections_only_include_resolved_specs(self):
        lock = '''GEM
  remote: https://user:private-token@registry.example.test/
  specs:
    Rails (7.1.0)
      activesupport (= 7.1.0)
    My_Gem (2.0.0)
GIT
  remote: https://user:secret@example.test/project.git
  revision: abc123
  specs:
    git-gem (1.0)
PATH
  remote: .
  specs:
    my.gem (3.0)
DEPENDENCIES
  something-not-resolved (~> 2)
'''
        result = parse_gemfile_lock(lock)
        self.assertEqual(result, ['git-gem', 'my-gem', 'rails'])
        self.assertNotIn('private-token', str(result))
        self.assertNotIn('activesupport', str(result))

    def test_does_not_include_plain_dependency_lines(self):
        self.assertEqual(parse_gemfile_lock('DEPENDENCIES\n  rails (~> 7)\nBUNDLED WITH\n   2.5.0\n'), [])

    def test_ignores_malformed_and_control_char_names(self):
        data = 'GEM\n  specs:\n    gem\n    other\x1b[31m (1.0)\n    valid (1.0)\n'
        self.assertEqual(parse_gemfile_lock(data), ['valid'])


if __name__ == '__main__':
    unittest.main()
