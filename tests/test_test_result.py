"""Regression tests for JSON-safe test runner result snapshots."""

import json
import unittest

from devpilot.test_result import snapshot_runner_result


class TestResultSnapshotTests(unittest.TestCase):
    def test_keeps_output_and_capture_flags(self):
        output = {'exit_code': 0, 'stdout': 'ok', 'stderr': '',
                  'stdout_truncated': False, 'stderr_truncated': True}
        self.assertEqual(snapshot_runner_result(output), output)

    def test_ignores_arbitrary_metadata_without_stringifying_it(self):
        class Dangerous:
            def __str__(self):
                raise AssertionError('must not inspect arbitrary objects')

            def __deepcopy__(self, memo):
                raise AssertionError('must not copy arbitrary objects')

        result = {'exit_code': 0, 'stdout': 'done', 'private_context': Dangerous(),
                  'argv': ['secret-token'], 'debug_data': {1, 2}}
        snapshot = snapshot_runner_result(result)
        self.assertEqual(snapshot, {'exit_code': 0, 'stdout': 'done'})
        self.assertEqual(json.loads(json.dumps(snapshot)), snapshot)

    def test_invalid_capture_flag_is_a_failure_diagnostic(self):
        for invalid in (None, 0, 'false', object()):
            with self.subTest(invalid=repr(type(invalid))):
                snapshot = snapshot_runner_result({'exit_code': 0,
                                                   'stdout_truncated': invalid})
                self.assertEqual(snapshot['error'], 'Test runner returned invalid capture metadata')
                self.assertNotIn('stdout_truncated', snapshot)
                self.assertEqual(json.loads(json.dumps(snapshot))['exit_code'], 0)


class TestExecutionIntegrationTests(unittest.TestCase):
    def test_json_report_survives_unknown_runner_metadata(self):
        from pathlib import Path
        from devpilot.test_execution import execute_test_commands

        class NotSerializable:
            def __deepcopy__(self, memo):
                raise AssertionError('not meant to be copied')

        commands = [{'argv': ['fake-test'], 'ecosystem': 'fake', 'reason': 'regression'}]
        self.assertTrue(execute_test_commands(
            commands, Path('/tmp'), 10,
            lambda *args: {'exit_code': 0, 'stdout': 'ok', 'internal': NotSerializable()},
        ))
        self.assertEqual(json.loads(json.dumps(commands))[0]['result'],
                         {'exit_code': 0, 'stdout': 'ok'})

    def test_invalid_capture_metadata_makes_execution_fail(self):
        from pathlib import Path
        from devpilot.test_execution import execute_test_commands

        commands = [{'argv': ['fake-test'], 'ecosystem': 'fake'}]
        self.assertFalse(execute_test_commands(
            commands, Path('/tmp'), 10,
            lambda *args: {'exit_code': 0, 'stdout_truncated': object()},
        ))
        self.assertIn('invalid capture metadata', commands[0]['result']['error'])


if __name__ == '__main__':
    unittest.main()
