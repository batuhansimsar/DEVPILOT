"""The dependency inventory must not claim completeness after skipping subtrees."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from devpilot.deps import MAX_DEPTH, main, scan


class DependencyDepthLimitTests(unittest.TestCase):
    def test_depth_limited_scan_reports_incomplete_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'go.mod').write_text('require example.org/root v1.0.0\n')
            capped = root.joinpath(*(["level"] * MAX_DEPTH))
            omitted = capped / 'deeper'
            omitted.mkdir(parents=True)
            (omitted / 'go.mod').write_text('require example.org/deep v1.0.0\n')
            report = scan(root)
            self.assertEqual(report['totals'], {'Go': 1})
            self.assertTrue(report['truncated'])
            self.assertEqual(len(report['warnings']), 1)
            self.assertIn('depth', report['warnings'][0].lower())
            self.assertNotIn(str(root), ' '.join(report['warnings']))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = main(['--path', str(root), '--json'])
            self.assertEqual(exit_code, 1)
            self.assertTrue(json.loads(output.getvalue())['truncated'])

    def test_ignored_and_symlinked_folders_do_not_trigger_depth_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            capped = root.joinpath(*(["level"] * MAX_DEPTH))
            capped.mkdir(parents=True)
            ignored = capped / 'node_modules'
            ignored.mkdir()
            (ignored / 'package.json').write_text('{bad')
            try:
                (capped / 'linked').symlink_to(ignored, target_is_directory=True)
            except OSError:
                pass  # Symlinks are optional on some platforms.
            report = scan(root)
            self.assertEqual(report['warnings'], [])
            self.assertFalse(report['truncated'])

    def test_manifest_exactly_at_depth_limit_is_included(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            capped = root.joinpath(*(["level"] * MAX_DEPTH))
            capped.mkdir(parents=True)
            (capped / 'requirements.txt').write_text('pytest>=8\n')
            report = scan(root)
            self.assertEqual(report['totals'], {'Python': 1})
            self.assertFalse(report['truncated'])


if __name__ == '__main__':
    unittest.main()
