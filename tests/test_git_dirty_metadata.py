"""Git status must not claim a clean worktree for malformed dirty metadata."""

import unittest

from devpilot.git_output import format_git_status


class _DangerousValue:
    def __bool__(self):
        raise AssertionError('untrusted values must not be coerced')

    def __str__(self):
        raise AssertionError('untrusted values must not be exposed')


class GitDirtyMetadataTests(unittest.TestCase):
    def test_invalid_dirty_values_are_inconclusive(self):
        for value in (_DangerousValue(), 'false', 0, [], {}):
            with self.subTest(type=type(value).__name__):
                output = format_git_status({'exit_code': 0, 'stdout': '', 'dirty': value})
                self.assertIn('Git status unavailable (invalid worktree state)', output)
                self.assertNotIn('No changes', output)

    def test_invalid_dirty_is_disclosed_even_with_porcelain_output(self):
        output = format_git_status({'exit_code': 0, 'stdout': '## main\n', 'dirty': _DangerousValue()})
        self.assertTrue(output.startswith('## main\n'))
        self.assertIn('invalid worktree state', output)

    def test_boolean_and_inconclusive_dirty_values_keep_existing_behavior(self):
        self.assertEqual(format_git_status({'exit_code': 0, 'stdout': '', 'dirty': False}), 'No changes')
        self.assertIn('reports changes', format_git_status({'exit_code': 0, 'stdout': '', 'dirty': True}))
        self.assertIn('state inconclusive', format_git_status({'exit_code': 0, 'stdout': '', 'dirty': None}))


if __name__ == '__main__':
    unittest.main()
