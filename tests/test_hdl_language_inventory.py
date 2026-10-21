"""Integration coverage for HDL source inventories in the Python analyzer."""

import tempfile
import unittest
from pathlib import Path

from devpilot.core import analyze_project


class HDLLanguageInventoryTests(unittest.TestCase):
    def test_analyze_recognizes_vhdl_and_systemverilog_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in (
                "logic.vhd", "entity.VHDL", "testbench.sv", "types.SVH",
                "design.v", "logic.vhd.bak",
            ):
                (root / name).write_text("-- content is not parsed", encoding="utf-8")

            report = analyze_project(root)
            self.assertFalse(report["truncated"], report["problems"])
            self.assertEqual(report["languages"].get("VHDL"), 2)
            self.assertEqual(report["languages"].get("SystemVerilog"), 2)
            # Ambiguous .v and backup files should not be classified as HDL.
            self.assertEqual(sum(report["languages"].values()), 4)


if __name__ == "__main__":
    unittest.main()
