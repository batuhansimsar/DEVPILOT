"""package.json scanner regression tests for overflowing JSON numeric metadata."""

import tempfile
import unittest
from pathlib import Path

from devpilot.deps import scan


class PackageJSONFiniteNumbersTests(unittest.TestCase):
    def test_nonfinite_exponents_are_rejected_without_disclosing_metadata(self):
        for number in ("1e9999", "-1E9999", "9.9e9999"):
            with self.subTest(number=number), tempfile.TemporaryDirectory() as directory:
                (Path(directory) / "package.json").write_text(
                    '{"metadata":{"private_token":"do-not-disclose","weight":'
                    + number + '},"dependencies":{"react":"^18"}}',
                    encoding="utf-8",
                )
                report = scan(directory)
                self.assertEqual(report["manifests"], [])
                self.assertEqual(len(report["warnings"]), 1)
                self.assertIn("non-finite JSON number", report["warnings"][0])
                self.assertNotIn("do-not-disclose", str(report))
                self.assertNotIn("private_token", str(report))

    def test_finite_exponent_in_metadata_does_not_change_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "package.json").write_text(
                '{"metadata":{"weight":1.25e2},"dependencies":{"react":"^18"}}',
                encoding="utf-8",
            )
            report = scan(directory)
        self.assertEqual(report["warnings"], [])
        self.assertEqual(report["manifests"][0]["groups"], {"dependencies": ["react"]})


if __name__ == "__main__":
    unittest.main()
