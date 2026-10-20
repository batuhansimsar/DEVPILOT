"""Version fields in Bundler lockfiles must be valid, not arbitrary metadata."""

import unittest

from devpilot.gemfile_lock import parse_gemfile_lock


class GemfileLockVersionTests(unittest.TestCase):
    def test_accepts_normal_versions_and_platform_suffixes(self):
        lock = ('GEM\n  specs:\n'
                '    Normal_Gem (1.0.0)\n'
                '    pre-release (2.0.0.rc1)\n'
                '    platform-gem (3.1.0-x86_64-linux)\n'
                '    java-gem (2.0.0-java)\n')
        self.assertEqual(parse_gemfile_lock(lock),
                         ['java-gem', 'normal-gem', 'platform-gem', 'pre-release'])

    def test_rejects_malformed_or_untrusted_version_fields(self):
        lock = ('GEM\n  specs:\n'
                '    empty ()\n'
                '    url (https://user:secret@example.invalid/)\n'
                '    nested (1.0 (ruby))\n'
                '    whitespace (1.0 ruby)\n'
                '    terminal (1.0\x1b[31m)\n'
                '    bogus (whatever)\n'
                '    valid (4.5.6+metadata)\n')
        names = parse_gemfile_lock(lock)
        self.assertEqual(names, ['valid'])
        self.assertNotIn('secret', str(names))

    def test_non_spec_metadata_remains_ignored(self):
        lock = ('GIT\n  remote: https://user:token@example.invalid/repo\n'
                '  specs:\n    kept (1)\n'
                'DEPENDENCIES\n  fake (2)\n')
        self.assertEqual(parse_gemfile_lock(lock), ['kept'])


if __name__ == '__main__':
    unittest.main()
