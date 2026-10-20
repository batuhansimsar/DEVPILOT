"""Protect selected test plans from mutating custom runners."""

import unittest
from pathlib import Path

from devpilot.test_execution import execute_test_commands


class TestCommandArgumentIsolation(unittest.TestCase):
    def setUp(self):
        self.commands = [
            {'ecosystem': 'Node.js', 'argv': ['npm', 'test']},
            {'ecosystem': 'Go', 'argv': ['go', 'test', './...']},
        ]
        self.root = Path('/tmp/project')

    def test_mutating_runner_cannot_change_reported_plan_or_later_runs(self):
        received = []

        def modifying_runner(argv, root, timeout):
            received.append(list(argv))
            argv[0] = 'unexpected'
            argv.append('--mutated')
            return {'exit_code': 0}

        self.assertTrue(execute_test_commands(self.commands, self.root, 10, modifying_runner))
        self.assertEqual(received, [['npm', 'test'], ['go', 'test', './...']])
        self.assertEqual([command['argv'] for command in self.commands], [
            ['npm', 'test'], ['go', 'test', './...']])
        self.assertTrue(execute_test_commands(self.commands, self.root, 10, modifying_runner))
        self.assertEqual(received[2:], received[:2])

    def test_mutation_then_failure_preserves_command_and_fail_fast_report(self):
        def crashing_runner(argv, root, timeout):
            argv.clear()
            raise RuntimeError('private information')

        self.assertFalse(execute_test_commands(
            self.commands, self.root, 10, crashing_runner, fail_fast=True))
        self.assertEqual(self.commands[0]['argv'], ['npm', 'test'])
        self.assertEqual(self.commands[0]['result']['error'], 'Test runner failed unexpectedly')
        self.assertEqual(self.commands[1]['argv'], ['go', 'test', './...'])
        self.assertIn('fail-fast', self.commands[1]['skipped_reason'])
        self.assertNotIn('result', self.commands[1])


if __name__ == '__main__':
    unittest.main()
