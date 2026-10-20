"""Safety regression tests for inspecting untrusted project directories.

These tests deliberately use only temporary files and never execute a
repository-provided script, shell command, or network service.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot import core


class UntrustedWorkspaceSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, content=""):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_symlinked_package_manifest_is_not_inspected(self):
        with tempfile.TemporaryDirectory() as external:
            real = Path(external) / "package.json"
            real.write_text('{"scripts":{"test":"echo unsafe"}}', encoding="utf-8")
            try:
                (self.root / "package.json").symlink_to(real)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            self.assertNotIn("Node.js", core.detect_projects(self.root))
            self.assertFalse(any(c["ecosystem"] == "Node.js" for c in core.test_commands(self.root)))

    def test_symlinked_dotnet_solution_is_not_detected(self):
        with tempfile.TemporaryDirectory() as external:
            real = Path(external) / "Outside.sln"
            real.write_text("", encoding="utf-8")
            try:
                (self.root / "Outside.sln").symlink_to(real)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable")
            self.assertNotIn(".NET", core.detect_projects(self.root))
            self.assertFalse(any(c["ecosystem"] == ".NET" for c in core.test_commands(self.root)))

    def test_analyze_never_echoes_local_environment_values(self):
        secret = "sensitive-data-must-not-appear-in-report"
        self.write(".env", "API_KEY=" + secret + "\n")
        self.write(".env.example", "API_KEY=placeholder\n")
        report = core.analyze_project(self.root)
        self.assertNotIn(secret, json.dumps(report))

    def test_package_script_discovery_cannot_execute_script(self):
        self.write("package.json", '{"scripts":{"test":"echo unsafe"}}')
        with patch.object(core.subprocess, "run", side_effect=AssertionError("must not execute")):
            commands = core.test_commands(self.root)
        self.assertTrue(any(cmd["ecosystem"] == "Node.js" for cmd in commands))

    def test_malformed_manifest_only_adds_diagnostic(self):
        self.write("package.json", "{not json")
        report = core.analyze_project(self.root)
        self.assertTrue(report["problems"])
        self.assertFalse(any(cmd["ecosystem"] == "Node.js" for cmd in core.test_commands(self.root)))

    def test_dependency_directory_is_not_recursively_scanned(self):
        self.write("node_modules/hidden.py", "password = 'do not read'")
        self.write("src/main.py", "print('hello')")
        report = core.analyze_project(self.root)
        self.assertEqual(report["languages"].get("Python"), 1)
        self.assertEqual(report["file_count"], 1)

    def test_invalid_tcp_port_is_rejected_before_connect(self):
        for port in (-1, 0, 65536):
            with self.subTest(port=port), patch.object(core.socket, "create_connection", side_effect=AssertionError("must not connect")):
                with self.assertRaises(ValueError):
                    core.tcp_check("127.0.0.1", port, 0.5)


if __name__ == "__main__":
    unittest.main()
