"""Regression tests for test runners that reuse mutable result buffers."""

import unittest
from pathlib import Path

from devpilot.test_execution import execute_test_commands


class TestResultSnapshotTests(unittest.TestCase):
    def test_reused_runner_mapping_does_not_rewrite_previous_outcome(self):
        commands = [{'argv': ['first']}, {'argv': ['second']}]
        reused = {'exit_code': 0, 'details': {'output': ['first passed']}}

        def runner(argv, root, timeout):
            if argv == ['second']:
                reused['exit_code'] = 1
                reused['details']['output'][0] = 'second failed'
            return reused

        self.assertFalse(execute_test_commands(commands, Path('/repo'), 5, runner))
        self.assertEqual(commands[0]['result'], {
            'exit_code': 0, 'details': {'output': ['first passed']},
        })
        self.assertEqual(commands[1]['result'], {
            'exit_code': 1, 'details': {'output': ['second failed']},
        })
        self.assertIsNot(commands[0]['result'], commands[1]['result'])
        self.assertIsNot(commands[0]['result']['details'], commands[1]['result']['details'])

    def test_mutations_after_run_do_not_change_stored_result(self):
        command = [{'argv': ['test']}]
        shared = {'exit_code': 0, 'stdout': ['ok']}
        self.assertTrue(execute_test_commands(command, Path('/repo'), 5,
                                              lambda *_: shared))
        shared['exit_code'] = 2
        shared['stdout'].append('later output')
        self.assertEqual(command[0]['result'], {'exit_code': 0, 'stdout': ['ok']})


if __name__ == '__main__':
    unittest.main()
