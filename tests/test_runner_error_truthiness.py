"""Hostile custom runner error objects must not be evaluated or disclosed."""

import json
import unittest
from pathlib import Path

from devpilot.test_execution import execute_test_commands


class _UntrustedError:
    def __bool__(self):
        raise AssertionError('private error __bool__ must not run')

    def __eq__(self, other):
        raise AssertionError('private error __eq__ must not run')

    def __repr__(self):
        raise AssertionError('private error __repr__ must not run')


class _UntrustedString(str):
    def __bool__(self):
        raise AssertionError('private string __bool__ must not run')

    def __eq__(self, other):
        raise AssertionError('private string __eq__ must not run')


class RunnerErrorTruthinessTests(unittest.TestCase):
    def test_invalid_exit_code_and_hostile_error_are_redacted(self):
        commands = [{'argv': ['first']}, {'argv': ['second']}]
        calls = []

        def runner(argv, root, timeout):
            calls.append(argv)
            return {'exit_code': None, 'error': _UntrustedError()}

        self.assertFalse(execute_test_commands(commands, Path('.'), 5, runner, fail_fast=True))
        self.assertEqual(calls, [['first']])
        self.assertEqual(commands[0]['result'], {
            'exit_code': None, 'error': 'Test runner returned an invalid error message',
        })
        self.assertIn('skipped_reason', commands[1])
        json.dumps(commands)

    def test_hostile_string_subclass_is_redacted_even_on_zero_exit(self):
        commands = [{'argv': ['first']}]
        result = {'exit_code': 0, 'stdout': object(), 'error': _UntrustedString('private-token')}
        self.assertFalse(execute_test_commands(commands, Path('.'), 5, lambda *_: result))
        self.assertEqual(commands[0]['result'], {
            'exit_code': 0, 'error': 'Test runner returned an invalid error message',
        })
        self.assertNotIn('private-token', json.dumps(commands))

    def test_empty_error_and_invalid_exit_preserves_existing_diagnostic(self):
        commands = [{'argv': ['first']}]
        self.assertFalse(execute_test_commands(commands, Path('.'), 5,
                                               lambda *_: {'exit_code': False, 'error': ''}))
        self.assertEqual(commands[0]['result']['error'], 'Test runner returned an invalid exit code')


if __name__ == '__main__':
    unittest.main()
