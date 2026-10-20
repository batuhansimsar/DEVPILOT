"""Regression tests for incomplete dependency inventories caused by filesystem errors."""

import contextlib
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from devpilot.deps import main, scan


class DependencyScanErrorsTests(unittest.TestCase):
    def test_scandir_failure_reports_partial_inventory_without_absolute_path(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'go.mod').write_text('module demo')

            def broken_walk(path, *, followlinks=False, onerror=None):
                self.assertFalse(followlinks)
                yield str(root), ['private'], ['go.mod']
                onerror(PermissionError(13, 'Access denied', str(root / 'private')))

            with patch('devpilot.walk.os.walk', side_effect=broken_walk):
                report = scan(root)

            self.assertEqual(len(report['manifests']), 1)
            self.assertTrue(report['truncated'])
            self.assertEqual(len(report['warnings']), 1)
            self.assertIn('private', report['warnings'][0])
            self.assertNotIn(str(root), json.dumps(report['warnings']))

    def test_cli_fails_instead_of_claiming_success_for_incomplete_scan(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)

            def broken_walk(path, *, followlinks=False, onerror=None):
                yield str(root), [], []
                onerror(PermissionError(13, 'Access denied', str(root / 'restricted')))

            output = io.StringIO()
            with patch('devpilot.walk.os.walk', side_effect=broken_walk), contextlib.redirect_stdout(output):
                code = main(['--path', str(root), '--json'])

            report = json.loads(output.getvalue())
            self.assertEqual(code, 1)
            self.assertTrue(report['truncated'])
            self.assertEqual(len(report['warnings']), 1)

    def test_normal_empty_scan_is_complete(self):
        with TemporaryDirectory() as tmp:
            report = scan(Path(tmp))
            self.assertFalse(report['truncated'])
            self.assertEqual(report['warnings'], [])


if __name__ == '__main__':
    unittest.main()
