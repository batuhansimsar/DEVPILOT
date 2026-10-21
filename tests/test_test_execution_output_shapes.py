"""Malformed custom test-runner output must not break JSON or human reports."""

import json
import unittest
from pathlib import Path
from unittest.mock import Mock

from devpilot.test_execution import execute_test_commands


class RunnerOutputShapeTests(unittest.TestCase):
    def setUp(self):
        self.commands = [
            {'ecosystem': 'Python', 'argv': ['python', '-m', 'unittest'], 'reason': 'tests directory'},
            {'ecosystem': 'Go', 'argv': ['go', 'test', './...'], 'reason': 'go.mod'},
        ]

    def test_malformed_stdout_is_redacted_and_reportable(self):
        self.assertFalse(execute_test_commands(
            self.commands, Path('/tmp/project'), 5,
            Mock(return_value={'exit_code': 0, 'stdout': ['private data']}), fail_fast=True))
        self.assertNotIn('stdout', self.commands[0]['result'])
        self.assertEqual(self.commands[0]['result']['error'],
                         'Test runner returned invalid captured output')
        self.assertIn('skipped_reason', self.commands[1])
        self.assertNotIn('private data', json.dumps(self.commands))

    def test_malformed_stderr_is_not_silently_successful(self):
        self.assertFalse(execute_test_commands(
            self.commands, Path('/tmp/project'), 5,
            Mock(return_value={'exit_code': 0, 'stderr': b'private data'})))
        self.assertNotIn('stderr', self.commands[0]['result'])
        self.assertEqual(self.commands[0]['result']['error'],
                         'Test runner returned invalid captured output')
        json.dumps(self.commands)

    def test_non_string_error_message_redacted(self):
        self.assertFalse(execute_test_commands(
            self.commands, Path('/tmp/project'), 5,
            Mock(return_value={'exit_code': 0, 'error': ValueError('private data')}), fail_fast=True))
        self.assertEqual(self.commands[0]['result']['error'],
                         'Test runner returned an invalid error message')
        self.assertNotIn('private data', json.dumps(self.commands))

    def test_valid_output_unchanged(self):
        self.assertTrue(execute_test_commands(
            self.commands, Path('/tmp/project'), 5,
            Mock(return_value={'exit_code': 0, 'stdout': 'ok',
                               'stderr': '', 'metadata': {'chunks': [1]}})))
        self.assertEqual(self.commands[0]['result']['stdout'], 'ok')
        self.assertEqual(self.commands[0]['result']['metadata'], {'chunks': [1]})
