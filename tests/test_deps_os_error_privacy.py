"""Reject private path and OS-message disclosure from manifest read failures."""

import errno
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.deps import scan


class DependencyOSErrorPrivacyTests(unittest.TestCase):
    def test_permission_failure_reports_only_errno(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text("{}", encoding="utf-8")
            secret_path = str(root / "hidden-token-file")
            failure = PermissionError(errno.EACCES, "SECRET_INTERNAL_DETAIL", secret_path)
            with patch("devpilot.deps._parse", side_effect=failure):
                report = scan(root)

        self.assertEqual(report["manifests"], [])
        self.assertEqual(report["warnings"], ["package.json: EACCES"])
        self.assertNotIn("SECRET_INTERNAL_DETAIL", str(report))
        self.assertNotIn(secret_path, str(report["warnings"]))

    def test_unknown_os_error_does_not_echo_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "go.mod").write_text("module example.org/app\n", encoding="utf-8")
            with patch("devpilot.deps._parse",
                       side_effect=OSError(999999, "PRIVATE_ERROR_MESSAGE")):
                report = scan(root)

        self.assertEqual(report["warnings"], ["go.mod: I/O error"])
        self.assertNotIn("PRIVATE_ERROR_MESSAGE", str(report))


if __name__ == "__main__":
    unittest.main()
