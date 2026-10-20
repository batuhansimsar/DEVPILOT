"""Executor errors should become safe test results instead of aborting a test report."""

import unittest
from pathlib import Path
from unittest.mock import Mock

from devpilot.test_execution import execute_test_commands


class RunnerExceptionTests(unittest.TestCase):
    def setUp(self):
        self.root = Path('/tmp/repo')
        self.commands = [
            {'ecosystem': 'Go', 'argv': ['go', 'test', './...']},
            {'ecosystem': 'Python', 'argv': ['python', '-m', 'unittest']},
        ]

    def test_os_error_is_private_failure_and_other_tests_still_run(self):
        runner = Mock(side_effect=[OSError('private/path/token'), {'exit_code': 0}])
        self.assertFalse(execute_test_commands(self.commands, self.root, 5, runner))
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(self.commands[0]['result'], {
            'exit_code': None, 'error': 'Test command could not be executed (OS error)',
        })
        self.assertEqual(self.commands[1]['result']['exit_code'], 0)
        self.assertNotIn('token', str(self.commands))

    def test_fail_fast_marks_unrun_commands_after_runner_os_error(self):
        runner = Mock(side_effect=FileNotFoundError('secret test runner'))
        self.assertFalse(execute_test_commands(self.commands, self.root, 5, runner, fail_fast=True))
        runner.assert_called_once()
        self.assertEqual(self.commands[0]['result']['exit_code'], None)
        self.assertNotIn('result', self.commands[1])
        self.assertIn('fail-fast', self.commands[1]['skipped_reason'])
        self.assertNotIn('secret', str(self.commands))

    def test_programming_errors_are_not_silenced(self):
        with self.assertRaises(RuntimeError):
            execute_test_commands(self.commands, self.root, 5, Mock(side_effect=RuntimeError('bug')))


if __name__ == '__main__':
    unittest.main()
