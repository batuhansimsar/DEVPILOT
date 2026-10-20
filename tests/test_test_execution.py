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


    def test_reuse_after_fail_fast_removes_skip_and_runs_all(self):
        first_runner = Mock(return_value={'exit_code': 1})
        self.assertFalse(execute_test_commands(self.commands, self.root, 10, first_runner, fail_fast=True))
        self.assertIn('skipped_reason', self.commands[1])
        second_runner = Mock(return_value={'exit_code': 0})
        self.assertTrue(execute_test_commands(self.commands, self.root, 10, second_runner))
        self.assertEqual(second_runner.call_count, 2)
        self.assertEqual([c['result']['exit_code'] for c in self.commands], [0, 0])
        self.assertTrue(all('skipped_reason' not in c for c in self.commands))
        self.assertEqual(self.commands[0]['reason'], 'test script')

    def test_reuse_then_fail_fast_removes_previous_result_from_skipped_command(self):
        first_runner = Mock(return_value={'exit_code': 0})
        self.assertTrue(execute_test_commands(self.commands, self.root, 10, first_runner))
        self.assertIn('result', self.commands[1])
        second_runner = Mock(return_value={'exit_code': 1})
        self.assertFalse(execute_test_commands(self.commands, self.root, 10, second_runner, fail_fast=True))
        second_runner.assert_called_once()
        self.assertNotIn('result', self.commands[1])
        self.assertIn('fail-fast', self.commands[1]['skipped_reason'])



    def test_runner_without_exit_code_is_reported_as_failure(self):
        runner = Mock(return_value={'stdout': 'completed but status unknown'})
        self.assertFalse(execute_test_commands(self.commands, self.root, 10, runner, fail_fast=True))
        self.assertIsNone(self.commands[0]['result']['exit_code'])
        self.assertEqual(self.commands[0]['result']['error'], 'Test runner returned an invalid exit code')
        self.assertIn('fail-fast', self.commands[1]['skipped_reason'])

    def test_runner_invalid_exit_codes_never_succeed(self):
        for invalid in (True, False, '0', 0.0, None):
            with self.subTest(invalid=invalid):
                self.assertFalse(execute_test_commands(
                    self.commands, self.root, 10, Mock(return_value={'exit_code': invalid})))
                self.assertIsNone(self.commands[0]['result']['exit_code'])
                self.assertEqual(self.commands[0]['result']['error'], 'Test runner returned an invalid exit code')

    def test_runner_error_is_preserved_when_exit_code_invalid(self):
        self.assertFalse(execute_test_commands(
            self.commands, self.root, 10, Mock(return_value={'exit_code': None, 'error': 'timeout'})))
        self.assertIsNone(self.commands[0]['result']['exit_code'])
        self.assertEqual(self.commands[0]['result']['error'], 'timeout')


if __name__ == '__main__':
    unittest.main()
