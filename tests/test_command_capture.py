"""Regression tests for bounded command output and Docker response parsing."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.core import command_result, docker_status


class CommandCaptureTests(unittest.TestCase):
    def test_large_stdout_and_stderr_are_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            report = command_result(
                [sys.executable, "-c",
                 'import sys; print("X"*25000); print("Y"*26000, file=sys.stderr)'],
                Path(directory), timeout=5,
            )
        self.assertEqual(report["exit_code"], 0)
        self.assertLessEqual(len(report["stdout"]), 20000)
        self.assertLessEqual(len(report["stderr"]), 20000)
        self.assertTrue(report["stdout_truncated"])
        self.assertTrue(report["stderr_truncated"])

    def test_small_output_is_not_truncated(self):
        with tempfile.TemporaryDirectory() as directory:
            report = command_result(
                [sys.executable, "-c", 'print("ok")'], Path(directory),
            )
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(report["stdout"].strip(), "ok")
        self.assertFalse(report["stdout_truncated"])
        self.assertFalse(report["stderr_truncated"])

    def test_missing_executable_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            report = command_result(
                ["missing-devpilot-command-987654321"], Path(directory),
            )
        self.assertIsNone(report["exit_code"])
        self.assertIn("error", report)

    def test_truncated_docker_json_is_not_reported_as_complete(self):
        fake = {
            "argv": ["docker", "ps", "--format", "{{json .}}"],
            "exit_code": 0,
            "stdout": '{"Names":"partial"}',
            "stderr": "",
            "stdout_truncated": True,
            "stderr_truncated": False,
        }
        with tempfile.TemporaryDirectory() as directory:
            with patch("devpilot.core.command_result", return_value=fake):
                report = docker_status(Path(directory))
        self.assertEqual(report["exit_code"], 1)
        self.assertEqual(report["containers"], [])
        self.assertIn("incomplete", report["error"])


if __name__ == "__main__":
    unittest.main()
