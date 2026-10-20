"""Guard against confusing source metadata with resolved gem specs."""

import unittest

from devpilot.gemfile_lock import parse_gemfile_lock


class GemfileLockScopeTests(unittest.TestCase):
    def test_source_metadata_terminates_specs(self):
        lock = (
            'GEM\n'
            '  specs:\n'
            '    valid-gem (1.0.0)\n'
            '      child-dependency (~> 2)\n'
            '  remote: https://user:secret@example.invalid/\n'
            '    injected-gem (2.0.0)\n'
            'DEPENDENCIES\n'
            '  valid-gem\n'
        )
        self.assertEqual(parse_gemfile_lock(lock), ['valid-gem'])

    def test_nested_specs_label_cannot_start_source_specs(self):
        lock = (
            'GIT\n'
            '    specs:\n'
            '    injected-gem (1.0)\n'
            '  remote: https://example.invalid/project\n'
            '  specs:\n'
            '    real-gem (1.0)\n'
        )
        self.assertEqual(parse_gemfile_lock(lock), ['real-gem'])

    def test_valid_separate_source_sections(self):
        lock = (
            'GEM\n  remote: https://example.invalid/\n  specs:\n    first_gem (1)\n'
            'GIT\n  revision: abc\n  specs:\n    second.gem (2)\n'
            'PATH\n  remote: .\n  specs:\n    third-gem (3)\n'
        )
        self.assertEqual(parse_gemfile_lock(lock), ['first-gem', 'second-gem', 'third-gem'])


if __name__ == '__main__':
    unittest.main()
