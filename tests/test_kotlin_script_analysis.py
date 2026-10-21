"""Kotlin script files contribute to accurate project-language statistics."""

import tempfile
import unittest
from pathlib import Path

from devpilot.core import analyze_project


class KotlinScriptAnalysisTests(unittest.TestCase):
    def test_gradle_kotlin_dsl_files_are_counted_as_kotlin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'settings.gradle.kts').write_text('rootProject.name = "sample"\n', encoding='utf-8')
            (root / 'build.gradle.kts').write_text('plugins {}\n', encoding='utf-8')
            (root / 'Main.kt').write_text('fun main() {}\n', encoding='utf-8')

            report = analyze_project(root)

        self.assertEqual(report['languages'], {'Kotlin': 3})
        self.assertIn('Java', report['project_types'])
        self.assertIn('settings.gradle.kts', report['key_files'])
        self.assertIn('build.gradle.kts', report['key_files'])

    def test_standalone_kotlin_script_is_counted_without_build_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'script.kts').write_text('println("hello")\n', encoding='utf-8')

            report = analyze_project(root)

        self.assertEqual(report['languages'], {'Kotlin': 1})
        self.assertEqual(report['project_types'], [])


if __name__ == '__main__':
    unittest.main()
