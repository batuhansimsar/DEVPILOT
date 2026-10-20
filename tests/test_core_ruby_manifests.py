"""Ensure root diagnostics recognize Ruby projects, including Bundler alternatives."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.core import analyze_project, detect_projects, doctor_report


class RubyRootDiagnosticsTests(unittest.TestCase):
    def test_root_bundler_files_are_key_files_and_detect_ruby(self):
        for name in ('Gemfile', 'Gemfile.lock', 'gems.rb', 'gems.locked'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / name).write_text('', encoding='utf-8')
                self.assertIn('Ruby', detect_projects(root))
                self.assertIn(name, analyze_project(root)['key_files'])

    def test_gemspec_only_root_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'library.GEMSPEC').write_text('', encoding='utf-8')
            self.assertIn('Ruby', detect_projects(root))
            self.assertIn('library.GEMSPEC', analyze_project(root)['key_files'])

    def test_symlinked_lockfile_cannot_trigger_ruby_detection(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as other:
            root = Path(directory)
            external = Path(other) / 'gems.locked'
            external.write_text('GEM\n  specs:\n    private (1)\n')
            try:
                (root / 'gems.locked').symlink_to(external)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unsupported')
            self.assertNotIn('Ruby', detect_projects(root))
            self.assertNotIn('gems.locked', analyze_project(root)['key_files'])

    def test_doctor_requires_ruby_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'gems.locked').write_text('', encoding='utf-8')
            with patch('devpilot.core.shutil.which', return_value=None):
                report = doctor_report(root)
            self.assertIn('Missing ruby required by detected project',
                          report['warnings'])


if __name__ == '__main__':
    unittest.main()
