"""C++ headers and module sources must appear in language inventory."""

import tempfile
import unittest
from pathlib import Path

from devpilot.core import analyze_project


class CppExtensionTests(unittest.TestCase):
    def test_common_cpp_extensions_are_counted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in (
                'engine.cxx', 'widget.hpp', 'widget.hxx', 'vector.HH',
                'module.ixx', 'module.cppm', 'helpers.ipp', 'shared.h',
            ):
                (root / name).write_text('// test fixture\n', encoding='utf-8')
            report = analyze_project(root)
        self.assertEqual(report['file_count'], 8)
        self.assertEqual(report['languages'].get('C++'), 7)
        self.assertEqual(report['languages'].get('C/C++'), 1)
        self.assertFalse(report['truncated'])


if __name__ == '__main__':
    unittest.main()
