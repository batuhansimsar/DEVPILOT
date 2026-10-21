"""Custom dict subclasses cannot forge test outcomes or crash reporting."""

import unittest
from pathlib import Path

from devpilot.test_execution import execute_test_commands


class _MisleadingStatus(dict):
    def get(self, key, default=None):
        if key == 'exit_code':
            return 0
        return super().get(key, default)


class _ThrowingStatus(dict):
    def get(self, key, default=None):
        raise RuntimeError('private-runner-secret')


class RunnerMappingSubclassTests(unittest.TestCase):
    def test_overridden_get_cannot_hide_failure(self):
        commands = [{'argv': ['first']}, {'argv': ['second']}]
        ran = []

        def runner(argv, root, timeout):
            ran.append(argv)
            return _MisleadingStatus(exit_code=9)

        self.assertFalse(execute_test_commands(commands, Path('.'), 5, runner, fail_fast=True))
        self.assertEqual(ran, [['first']])
        self.assertEqual(commands[0]['result'], {'exit_code': 9})
        self.assertIn('skipped_reason', commands[1])

    def test_overridden_get_cannot_crash_reporting(self):
        commands = [{'argv': ['first']}]
        self.assertTrue(execute_test_commands(
            commands, Path('.'), 5,
            lambda argv, root, timeout: _ThrowingStatus(exit_code=0),
        ))
        self.assertEqual(commands[0]['result'], {'exit_code': 0})
        self.assertNotIn('private-runner-secret', repr(commands))


if __name__ == '__main__':
    unittest.main()
