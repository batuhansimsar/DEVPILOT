import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from devpilot.core import analyze_project


class AnalyzeDepthRegressionTests(unittest.TestCase):
    def test_depth_limit_reports_incomplete_scan_and_keeps_siblings(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'a' / 'too-deep').mkdir(parents=True)
            (root / 'a' / 'too-deep' / 'hidden.py').touch()
            (root / 'z').mkdir()
            (root / 'z' / 'visible.py').touch()
            with patch('devpilot.core.MAX_DEPTH', 1):
                result = analyze_project(root)
            self.assertTrue(result['truncated'])
            self.assertEqual(result['languages'].get('Python'), 1)
            self.assertEqual(result['file_count'], 1)

    def test_depth_limit_without_skipped_children_is_complete(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'a').mkdir()
            (root / 'a' / 'visible.py').touch()
            with patch('devpilot.core.MAX_DEPTH', 1):
                result = analyze_project(root)
            self.assertFalse(result['truncated'])
            self.assertEqual(result['file_count'], 1)

    def test_ignored_subdirectories_do_not_count_as_truncation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'node_modules').mkdir()
            (root / 'node_modules' / 'hidden.py').touch()
            with patch('devpilot.core.MAX_DEPTH', 0):
                result = analyze_project(root)
            self.assertFalse(result['truncated'])
            self.assertEqual(result['file_count'], 0)

    def test_file_limit_still_stops_at_limit(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'a.py').touch()
            (root / 'b.py').touch()
            with patch('devpilot.core.MAX_FILES', 1):
                result = analyze_project(root)
            self.assertTrue(result['truncated'])
            self.assertEqual(result['file_count'], 1)


if __name__ == '__main__':
    unittest.main()
