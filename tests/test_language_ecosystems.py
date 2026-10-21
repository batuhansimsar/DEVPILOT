"""Count Dart, Julia, Lua, Elixir and Zig sources in repository analysis."""

import tempfile
import unittest
from pathlib import Path

from devpilot.core import analyze_project


class MoreLanguageExtensionsTests(unittest.TestCase):
    def test_source_files_counted_without_manifests(self):
        samples = {
            'mobile/main.dart': 'Dart',
            'mobile/WIDGET.DART': 'Dart',
            'analysis/solver.jl': 'Julia',
            'scripts/init.lua': 'Lua',
            'service/main.ex': 'Elixir',
            'service/main_test.exs': 'Elixir',
            'compiler/main.zig': 'Zig',
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in samples:
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('// example\n', encoding='utf-8')
            report = analyze_project(root)
            self.assertEqual(report['file_count'], len(samples))
            self.assertEqual(report['languages'], {
                'Dart': 2, 'Elixir': 2, 'Julia': 1, 'Lua': 1, 'Zig': 1,
            })
            self.assertEqual(report['project_types'], [])
            self.assertEqual(report['key_files'], [])


if __name__ == '__main__':
    unittest.main()
