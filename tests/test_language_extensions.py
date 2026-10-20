"""Regression coverage for modern JavaScript and TypeScript source inventory."""

import tempfile
import unittest
from pathlib import Path

from devpilot.core import analyze_project


class LanguageExtensionsTests(unittest.TestCase):
    def test_modern_language_extensions_are_counted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            examples = {
                'client.mjs': 'JavaScript',
                'config.cjs': 'JavaScript',
                'worker.mts': 'TypeScript',
                'server.cts': 'TypeScript',
                'layout.astro': 'Astro',
                'UPPER.MJS': 'JavaScript',
            }
            for name in examples:
                (root / name).write_text('// example\n', encoding='utf-8')

            report = analyze_project(root)

            self.assertEqual(report['file_count'], len(examples))
            self.assertFalse(report['truncated'])
            self.assertEqual(report['languages'], {
                'JavaScript': 3,
                'TypeScript': 2,
                'Astro': 1,
            })


if __name__ == '__main__':
    unittest.main()
