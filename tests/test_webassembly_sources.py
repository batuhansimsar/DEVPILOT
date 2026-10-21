"""WebAssembly text and interface definitions appear in the Python inventory."""

import tempfile
import unittest
from pathlib import Path

from devpilot.core import analyze_project


class WebAssemblySourceTests(unittest.TestCase):
    def test_webassembly_text_and_wit_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for filename in ("module.wat", "tests.WAST", "interface.wit",
                             "nested/component.WIT", "module.wat.bak", "README.md"):
                path = root / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("source", encoding="utf-8")
            report = analyze_project(root)

        self.assertFalse(report["truncated"])
        self.assertEqual(report["file_count"], 6)
        self.assertEqual(report["languages"], {
            "WebAssembly Text": 2,
            "WebAssembly Interface Types": 2,
        })


if __name__ == "__main__":
    unittest.main()
