"""Dependency inventory must not traverse a linked root before checking it."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.deps import main, scan


class DependencyScanLinkedRootTests(unittest.TestCase):
    def test_symlinked_directory_is_rejected_without_walking(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            outside = base / 'outside'
            outside.mkdir()
            (outside / 'requirements.txt').write_text('secret-internal-package==1\n', encoding='utf-8')
            link = base / 'project'
            try:
                link.symlink_to(outside, target_is_directory=True)
            except (NotImplementedError, OSError):
                self.skipTest('directory symlinks unavailable')
            with patch('devpilot.deps.walk_project', side_effect=AssertionError('must not traverse')):
                with self.assertRaisesRegex(ValueError, 'symbolic link'):
                    scan(link)

    def test_dangling_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            link = Path(temporary) / 'project'
            try:
                link.symlink_to(Path(temporary) / 'missing', target_is_directory=True)
            except (NotImplementedError, OSError):
                self.skipTest('directory symlinks unavailable')
            with self.assertRaisesRegex(ValueError, 'symbolic link'):
                scan(link)

    def test_cli_fails_without_disclosing_external_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            outside = base / 'outside'
            outside.mkdir()
            (outside / 'requirements.txt').write_text('private-package==1', encoding='utf-8')
            link = base / 'project'
            try:
                link.symlink_to(outside, target_is_directory=True)
            except (NotImplementedError, OSError):
                self.skipTest('directory symlinks unavailable')
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                code = main(['--path', str(link), '--json'])
            self.assertEqual(code, 2)
            self.assertIn('symbolic link', errors.getvalue())
            self.assertNotIn('private-package', errors.getvalue())
            self.assertNotIn(str(outside), errors.getvalue())

    def test_regular_root_still_scans_dependencies(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'requirements.txt').write_text('requests==2\n', encoding='utf-8')
            report = scan(root)
            self.assertEqual(report['manifests'][0]['groups']['requirements'], ['requests'])
            self.assertFalse(report['truncated'])


if __name__ == '__main__':
    unittest.main()
