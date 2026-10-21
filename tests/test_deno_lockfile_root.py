"""Deno lockfile-only roots agree with nested workspace detection."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot import core
from devpilot.workspaces import discover_workspaces


class DenoLockfileRootTests(unittest.TestCase):
    def test_lockfile_only_root_is_detected_but_does_not_offer_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'deno.lock').write_text('{"version": "4", "specifiers": {}}', encoding='utf-8')

            self.assertEqual(core.detect_projects(root), ['Deno'])
            report = core.analyze_project(root)
            self.assertEqual(report['project_types'], ['Deno'])
            self.assertIn('deno.lock', report['key_files'])
            self.assertEqual(discover_workspaces(root)['workspaces'][0]['ecosystems'], ['Deno'])
            self.assertFalse(any(cmd['ecosystem'] == 'Deno' for cmd in core.test_commands(root)))

            with patch('devpilot.core.shutil.which', return_value=None), patch(
                'devpilot.security.tracked_environment_files', return_value=[]
            ):
                doctor = core.doctor_report(root)
            self.assertIn('Missing deno required by detected project', doctor['warnings'])

    def test_symlinked_lockfile_is_not_treated_as_root_project(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            target = Path(outside) / 'deno.lock'
            target.write_text('{}', encoding='utf-8')
            try:
                (root / 'deno.lock').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertNotIn('Deno', core.detect_projects(root))
            self.assertNotIn('deno.lock', core.analyze_project(root)['key_files'])


if __name__ == '__main__':
    unittest.main()
