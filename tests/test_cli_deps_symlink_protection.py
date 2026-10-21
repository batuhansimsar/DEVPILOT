"""Guard the CLI boundary around the dependency scanner's linked-root checks."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.cli import main


class DependencyCliLinkedRootTests(unittest.TestCase):
    def test_symlinked_root_is_rejected_before_scanning(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            outside = base / "outside"
            outside.mkdir()
            (outside / "requirements.txt").write_text(
                "confidential-package==1\n", encoding="utf-8"
            )
            linked = base / "chosen"
            try:
                linked.symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlinks unavailable")

            stderr = io.StringIO()
            with patch("devpilot.cli.dependency_scan",
                       side_effect=AssertionError("scanner must not be called")):
                with contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as caught:
                        main(["deps", "--path", str(linked), "--json"])

            self.assertEqual(caught.exception.code, 2)
            self.assertIn("symbolic link", stderr.getvalue())
            self.assertNotIn("confidential-package", stderr.getvalue())
            self.assertNotIn(str(outside), stderr.getvalue())

    def test_regular_root_is_passed_to_scanner_without_resolution(self):
        with tempfile.TemporaryDirectory() as temporary:
            selected = Path(temporary) / "project"
            selected.mkdir()
            report = {
                "root": str(selected), "manifests": [],
                "totals": {}, "warnings": [], "truncated": False,
            }
            output = io.StringIO()
            with patch("devpilot.cli.dependency_scan", return_value=report) as scan:
                with contextlib.redirect_stdout(output):
                    status = main(["deps", "--path", str(selected), "--json"])

            self.assertEqual(status, 0)
            scan.assert_called_once_with(selected)
            self.assertIn('"manifests": []', output.getvalue())

    def test_raced_symlink_error_is_private_and_returns_exit_two(self):
        with tempfile.TemporaryDirectory() as temporary:
            selected = Path(temporary) / "project"
            selected.mkdir()
            stderr = io.StringIO()
            with patch("devpilot.cli.dependency_scan",
                       side_effect=ValueError("private directory /secret/location")):
                with contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as caught:
                        main(["deps", "--path", str(selected), "--json"])

            self.assertEqual(caught.exception.code, 2)
            self.assertIn("Cannot scan dependency directory", stderr.getvalue())
            self.assertNotIn("/secret/location", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
