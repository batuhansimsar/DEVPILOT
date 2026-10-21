"""Root-level project diagnostics must agree with workspace manifest discovery."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot import core


class RootManifestDetectionTests(unittest.TestCase):
    def test_go_work_only_root_detected_without_unsafe_root_test_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'go.work').write_text('go 1.23\nuse ./service\n', encoding='utf-8')
            report = core.analyze_project(root)
            self.assertIn('Go', report['project_types'])
            self.assertIn('go.work', report['key_files'])
            # go test ./... from a workspace root outside modules is invalid.
            self.assertFalse(any(c['ecosystem'] == 'Go' for c in core.test_commands(root)))
            with patch('devpilot.core.shutil.which', return_value=None):
                self.assertIn('Missing go required by detected project', core.doctor_report(root)['warnings'])

    def test_python_lockfile_only_roots_are_detected(self):
        for name, content in [('uv.lock', 'version = 1\n'), ('poetry.lock', 'package = []\n')]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / name).write_text(content, encoding='utf-8')
                (root / 'tests').mkdir()
                (root / 'tests' / 'test_example.py').touch()
                self.assertIn('Python', core.detect_projects(root))
                self.assertIn(name, core.analyze_project(root)['key_files'])
                self.assertTrue(any(c['ecosystem'] == 'Python' for c in core.test_commands(root)))


if __name__ == '__main__':
    unittest.main()
