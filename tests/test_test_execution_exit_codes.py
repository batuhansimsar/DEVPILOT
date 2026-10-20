"""Only a genuine integer process exit code of zero indicates success."""

import unittest
from pathlib import Path

from devpilot.test_execution import execute_test_commands


class TestExecutionExitCodeTests(unittest.TestCase):
    def test_boolean_and_numeric_coercions_are_not_success(self):
        for value in (False, 0.0, '0', None):
            with self.subTest(exit_code=repr(value)):
                commands = [{'argv': ['one']}, {'argv': ['two']}]
                calls = []

                def runner(argv, root, timeout):
                    calls.append(argv)
                    return {'exit_code': value}

                self.assertFalse(execute_test_commands(
                    commands, Path('/tmp'), 2, runner, fail_fast=True))
                self.assertEqual(calls, [['one']])
                self.assertEqual(
                    commands[1]['skipped_reason'],
                    'previous test command failed (--fail-fast)')

    def test_integer_zero_remains_successful(self):
        commands = [{'argv': ['one']}]
        self.assertTrue(execute_test_commands(
            commands, Path('/tmp'), 2,
            lambda argv, root, timeout: {'exit_code': 0}))
        self.assertEqual(commands[0]['result']['exit_code'], 0)


if __name__ == '__main__':
    unittest.main()
