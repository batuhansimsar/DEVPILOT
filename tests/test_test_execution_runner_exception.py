"""Unexpected test runner exceptions must never leak private diagnostic data."""

import unittest
from pathlib import Path
from unittest.mock import Mock

from devpilot.test_execution import execute_test_commands


class TestRunnerExceptionTests(unittest.TestCase):
    def setUp(self):
        self.commands = [
            {'argv': ['npm', 'test']},
            {'argv': ['go', 'test', './...']},
        ]
        self.root = Path('/tmp/repo')

    def test_unexpected_exception_is_redacted_and_other_commands_continue(self):
        runner = Mock(side_effect=[RuntimeError('token=super-secret /private/home'), {'exit_code': 0}])
        self.assertFalse(execute_test_commands(self.commands, self.root, 10, runner))
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(self.commands[0]['result'], {
            'exit_code': None, 'error': 'Test runner failed unexpectedly',
        })
        self.assertNotIn('super-secret', str(self.commands))
        self.assertEqual(self.commands[1]['result']['exit_code'], 0)

    def test_unexpected_exception_respects_fail_fast(self):
        runner = Mock(side_effect=ValueError('private credentials in exception'))
        self.assertFalse(execute_test_commands(self.commands, self.root, 10, runner, fail_fast=True))
        runner.assert_called_once()
        self.assertIn('fail-fast', self.commands[1]['skipped_reason'])
        self.assertNotIn('result', self.commands[1])
        self.assertNotIn('private credentials', str(self.commands))


if __name__ == '__main__':
    unittest.main()
