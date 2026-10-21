"""Clojure root-project detection and safe test command selection."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.core import analyze_project, detect_projects, doctor_report, test_commands
from devpilot.test_selection import select_test_commands


class ClojureRootTests(unittest.TestCase):
    def test_tools_deps_project_has_no_assumed_test_alias(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'deps.edn').write_text('{:paths ["src"]}', encoding='utf-8')
            (root / 'main.clj').write_text('(ns app.core)', encoding='utf-8')
            self.assertEqual(detect_projects(root), ['Clojure'])
            analyzed = analyze_project(root)
            self.assertIn('deps.edn', analyzed['key_files'])
            self.assertEqual(analyzed['languages'], {'Clojure': 2})
            self.assertEqual(test_commands(root), [])
            with patch('devpilot.core.shutil.which', return_value=None):
                report = doctor_report(root)
            self.assertIn('Missing clojure required by detected project', report['warnings'])

    def test_leiningen_project_has_guarded_test_command(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'project.clj').write_text('(defproject demo "0.1.0")', encoding='utf-8')
            (root / 'core.cljs').write_text('(ns app.core)', encoding='utf-8')
            self.assertEqual(detect_projects(root), ['Clojure'])
            commands = test_commands(root)
            self.assertEqual(commands, [{
                'ecosystem': 'Clojure', 'argv': ['lein', 'test'], 'reason': 'project.clj',
            }])
            self.assertEqual(select_test_commands(commands, 'CLOJURE'), commands)
            with patch('devpilot.core.shutil.which', return_value=None):
                report = doctor_report(root)
            self.assertIn('Missing lein required by detected project', report['warnings'])

    def test_unrelated_and_symlinked_manifests_are_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'deps.edn.bak').write_text('', encoding='utf-8')
            (root / 'project.clj.disabled').write_text('', encoding='utf-8')
            self.assertEqual(detect_projects(root), [])
            self.assertEqual(test_commands(root), [])
            try:
                (root / 'deps.edn').symlink_to(root / 'deps.edn.bak')
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertEqual(detect_projects(root), [])


if __name__ == '__main__':
    unittest.main()
