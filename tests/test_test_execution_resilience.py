"""Test runner failures should be reported without crashing or leaking details."""

import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock

from devpilot.test_execution import execute_test_commands


class TestExecutionResilienceTests(unittest.TestCase):
    def setUp(self):
        self.root = Path('/private/repository')
        self.commands = [{'argv': ['tool', 'test']}, {'argv': ['other', 'test']}]

    def test_timeout_is_a_failure_without_leaking_exception_details(self):
        runner = Mock(side_effect=subprocess.TimeoutExpired(
            cmd=['tool', '/private/secret-token'], timeout=3, output=b'secret stdout',
            stderr=b'secret stderr',
        ))
        self.assertFalse(execute_test_commands(self.commands, self.root, 3, runner, fail_fast=True))
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(self.commands[0]['result'], {
            'exit_code': None, 'error': 'Test command timed out',
        })
        self.assertNotIn('secret', str(self.commands))
        self.assertNotIn('result', self.commands[1])
        self.assertIn('skipped_reason', self.commands[1])

    def test_invalid_runner_results_are_failures_and_execution_continues(self):
        for bad in (None, 0, [], 'success'):
            with self.subTest(bad=bad):
                commands = [{'argv': ['first']}, {'argv': ['second']}]
                runner = Mock(side_effect=[bad, {'exit_code': 0}])
                self.assertFalse(execute_test_commands(commands, self.root, 10, runner))
                self.assertEqual(runner.call_count, 2)
                self.assertEqual(commands[0]['result'], {
                    'exit_code': None, 'error': 'Test runner returned an invalid result',
                })
                self.assertEqual(commands[1]['result'], {'exit_code': 0})

    def test_timeout_does_not_poison_next_invocation(self):
        runner = Mock(side_effect=subprocess.TimeoutExpired(cmd='private', timeout=1))
        self.assertFalse(execute_test_commands(self.commands, self.root, 1, runner, fail_fast=True))
        self.assertTrue(execute_test_commands(self.commands, self.root, 1,
                                              Mock(return_value={'exit_code': 0})))
        self.assertEqual([item['result']['exit_code'] for item in self.commands], [0, 0])
        self.assertTrue(all('skipped_reason' not in item for item in self.commands))


if __name__ == '__main__':
    unittest.main()
