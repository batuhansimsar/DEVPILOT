"""A runner-level error cannot be masked by a zero process exit status."""

import unittest
from pathlib import Path
from unittest.mock import Mock

from devpilot.test_execution import execute_test_commands


class RunnerErrorFlagTests(unittest.TestCase):
    def setUp(self):
        self.root = Path('/tmp/project')
        self.commands = [{'argv': ['first']}, {'argv': ['second']}]

    def test_zero_exit_with_runner_error_does_not_pass(self):
        runner = Mock(side_effect=[
            {'exit_code': 0, 'error': 'output pipe could not be read'},
            {'exit_code': 0},
        ])
        self.assertFalse(execute_test_commands(self.commands, self.root, 10, runner))
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(self.commands[0]['result']['exit_code'], 0)

    def test_zero_exit_with_runner_error_stops_fail_fast(self):
        runner = Mock(return_value={'exit_code': 0, 'error': 'runner failed'})
        self.assertFalse(execute_test_commands(
            self.commands, self.root, 10, runner, fail_fast=True))
        runner.assert_called_once()
        self.assertNotIn('result', self.commands[1])
        self.assertIn('--fail-fast', self.commands[1]['skipped_reason'])

    def test_blank_error_does_not_change_success(self):
        runner = Mock(return_value={'exit_code': 0, 'error': ''})
        self.assertTrue(execute_test_commands(self.commands, self.root, 10, runner))
        self.assertEqual(runner.call_count, 2)


if __name__ == '__main__':
    unittest.main()
