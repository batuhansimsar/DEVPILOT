"""Unexpected copy failures must not crash CLI test execution or leak metadata."""

import unittest
from pathlib import Path

from devpilot.test_execution import execute_test_commands


class _Uncopyable:
    def __deepcopy__(self, memo):
        raise RuntimeError('private-token-do-not-print')


class TestExecutionCopyFailureTests(unittest.TestCase):
    def test_uncopyable_result_is_safe_failure_and_skips_next_in_fail_fast(self):
        commands = [{'argv': ['test-one']}, {'argv': ['test-two']}]
        called = []

        def runner(argv, root, timeout):
            called.append(argv)
            return {'exit_code': 0, 'metadata': _Uncopyable()}

        self.assertFalse(execute_test_commands(commands, Path('.'), 10, runner, fail_fast=True))
        self.assertEqual(called, [['test-one']])
        self.assertIsNone(commands[0]['result']['exit_code'])
        self.assertNotIn('private-token', repr(commands))
        self.assertIn('fail-fast', commands[1]['skipped_reason'])

    def test_uncopyable_first_result_does_not_stop_default_execution(self):
        commands = [{'argv': ['a']}, {'argv': ['b']}]
        count = 0

        def runner(argv, root, timeout):
            nonlocal count
            count += 1
            return {'exit_code': 0, 'metadata': _Uncopyable()} if count == 1 else {'exit_code': 0}

        self.assertFalse(execute_test_commands(commands, Path('.'), 10, runner))
        self.assertEqual(count, 2)
        self.assertEqual(commands[1]['result']['exit_code'], 0)


if __name__ == '__main__':
    unittest.main()
