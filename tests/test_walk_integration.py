"""Ensure analysis surfaces os.walk errors rather than claiming a complete scan."""

import errno
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.core import analyze_project


class WalkIntegrationTests(unittest.TestCase):
    def test_analyze_reports_directory_scan_failures(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            def fake_walk(path, *, followlinks, onerror):
                onerror(PermissionError(errno.EACCES, 'Permission denied', str(root / 'unreadable')))
                yield str(root), [], []

            with patch('devpilot.walk.os.walk', side_effect=fake_walk):
                report = analyze_project(root)
            self.assertIn('Cannot inspect unreadable: Permission denied', report['problems'])
            self.assertEqual(report['file_count'], 0)


if __name__ == '__main__':
    unittest.main()
