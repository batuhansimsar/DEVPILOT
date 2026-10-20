"""Regression tests for multi-ecosystem test execution policies."""

import unittest
from pathlib import Path
from unittest.mock import Mock

from devpilot.test_execution import execute_test_commands


class TestExecutionTests(unittest.TestCase):
    def setUp(self):
        self.commands = [
            {'ecosystem': 'Node.js', 'argv': ['npm', 'test'], 'reason': 'test script'},
            {'ecosystem': 'Go', 'argv': ['go', 'test', './...'], 'reason': 'go.mod'},
        ]
        self.root = Path('/tmp/repo')

    def test_fail_fast_skips_following_commands(self):
        runner = Mock(return_value={'exit_code': 1, 'stderr': 'failed'})
        self.assertFalse(execute_test_commands(self.commands, self.root, 60, runner, fail_fast=True))
        runner.assert_called_once_with(['npm', 'test'], self.root, 60)
        self.assertEqual(self.commands[0]['result']['exit_code'], 1)
        self.assertNotIn('result', self.commands[1])
        self.assertIn('fail-fast', self.commands[1]['skipped_reason'])

    def test_default_runs_all_even_after_failure(self):
        runner = Mock(side_effect=[{'exit_code': None, 'error': 'timeout'}, {'exit_code': 0}])
        self.assertFalse(execute_test_commands(self.commands, self.root, 30, runner))
        self.assertEqual(runner.call_count, 2)
        self.assertTrue(all('result' in item for item in self.commands))
        self.assertTrue(all('skipped_reason' not in item for item in self.commands))

    def test_both_successful(self):
        runner = Mock(return_value={'exit_code': 0})
        self.assertTrue(execute_test_commands(self.commands, self.root, 10, runner, fail_fast=True))
        self.assertEqual(runner.call_count, 2)

    def test_no_commands_does_not_invoke_runner(self):
        runner = Mock()
        self.assertFalse(execute_test_commands([], self.root, 10, runner, fail_fast=True))
        runner.assert_not_called()


if __name__ == '__main__':
    unittest.main()
