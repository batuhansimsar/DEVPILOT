"""Regression checks for rerunning an existing test plan."""
import unittest
from pathlib import Path
from unittest.mock import Mock

from devpilot.test_execution import execute_test_commands


class RerunReportTests(unittest.TestCase):
    def setUp(self):
        self.root = Path('/tmp')
        self.commands = [{'argv': ['first'], 'ecosystem': 'Go'}, {'argv': ['second'], 'ecosystem': 'Python'}]

    def test_rerun_clears_prior_skip_annotations(self):
        failed = Mock(return_value={'exit_code': 1})
        self.assertFalse(execute_test_commands(self.commands, self.root, 5, failed, fail_fast=True))
        self.assertIn('skipped_reason', self.commands[1])
        healthy = Mock(return_value={'exit_code': 0})
        self.assertTrue(execute_test_commands(self.commands, self.root, 5, healthy))
        self.assertEqual(healthy.call_count, 2)
        self.assertTrue(all('skipped_reason' not in c for c in self.commands))
        self.assertTrue(all(c['result']['exit_code'] == 0 for c in self.commands))

    def test_fail_fast_rerun_does_not_retain_old_success(self):
        healthy = Mock(return_value={'exit_code': 0})
        self.assertTrue(execute_test_commands(self.commands, self.root, 5, healthy))
        failing = Mock(return_value={'exit_code': 2})
        self.assertFalse(execute_test_commands(self.commands, self.root, 5, failing, fail_fast=True))
        self.assertEqual(failing.call_count, 1)
        self.assertNotIn('result', self.commands[1])
        self.assertIn('skipped_reason', self.commands[1])

    def test_empty_commands_are_not_executed(self):
        runner = Mock()
        self.assertFalse(execute_test_commands([], self.root, 5, runner))
        runner.assert_not_called()


if __name__ == '__main__':
    unittest.main()
