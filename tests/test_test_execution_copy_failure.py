"""Unknown runner metadata must be discarded without invoking copy hooks."""

import unittest
from pathlib import Path

from devpilot.test_execution import execute_test_commands


class _Uncopyable:
    def __deepcopy__(self, memo):
        raise RuntimeError('private-token-do-not-print')


class TestExecutionCopyFailureTests(unittest.TestCase):
    def test_unknown_metadata_is_discarded_without_copying_in_fail_fast(self):
        commands = [{'argv': ['test-one']}, {'argv': ['test-two']}]
        called = []

        def runner(argv, root, timeout):
            called.append(argv)
            return {'exit_code': 0, 'metadata': _Uncopyable()}

        self.assertTrue(execute_test_commands(commands, Path('.'), 10, runner, fail_fast=True))
        self.assertEqual(called, [['test-one'], ['test-two']])
        self.assertEqual(commands[0]['result'], {'exit_code': 0})
        self.assertNotIn('private-token', repr(commands))
        self.assertNotIn('skipped_reason', commands[1])

    def test_unknown_metadata_does_not_stop_default_execution(self):
        commands = [{'argv': ['a']}, {'argv': ['b']}]
        count = 0

        def runner(argv, root, timeout):
            nonlocal count
            count += 1
            return {'exit_code': 0, 'metadata': _Uncopyable()} if count == 1 else {'exit_code': 0}

        self.assertTrue(execute_test_commands(commands, Path('.'), 10, runner))
        self.assertEqual(count, 2)
        self.assertEqual(commands[1]['result']['exit_code'], 0)


if __name__ == '__main__':
    unittest.main()
