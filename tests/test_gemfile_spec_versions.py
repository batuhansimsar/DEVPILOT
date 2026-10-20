"""Malformed Bundler spec entries must not pollute gem inventories."""

import unittest

from devpilot.gemfile_lock import parse_gemfile_lock


class GemfileSpecVersionTests(unittest.TestCase):
    def test_invalid_empty_or_nonnumeric_versions_are_ignored(self):
        lock = ('GEM\n  specs:\n'
                '    empty ()\n'
                '    bogus (private-token)\n'
                '    real (1.2.3)\n')
        self.assertEqual(parse_gemfile_lock(lock), ['real'])

    def test_nested_or_control_character_versions_are_ignored(self):
        lock = ('PATH\n  specs:\n'
                '    nested (1.2 (bad))\n'
                '    control (1.2\x00oops)\n'
                '    good (2.0.0.pre)\n')
        self.assertEqual(parse_gemfile_lock(lock), ['good'])

    def test_platform_qualified_versions_and_other_sources_still_work(self):
        lock = ('GEM\n  remote: https://user:secret@example.invalid\n'
                '  specs:\n    Nokogiri (1.17.0-x86_64-linux)\n'
                'GIT\n  remote: https://user:secret@example.invalid/repo\n'
                '  specs:\n    My_Gem (0.1.0)\n')
        names = parse_gemfile_lock(lock)
        self.assertEqual(names, ['my-gem', 'nokogiri'])
        self.assertNotIn('secret', str(names))


if __name__ == '__main__':
    unittest.main()
