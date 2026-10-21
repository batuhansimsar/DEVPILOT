"""A UTF-8 BOM at the start of go.mod must not hide direct requirements."""

import unittest

from devpilot.go_mod import parse_go_requirements


class GoModBOMDirectTests(unittest.TestCase):
    def test_single_line_require_after_bom(self):
        self.assertEqual(
            parse_go_requirements("\ufeffrequire example.org/dependency v1.2.3\n"),
            ["example.org/dependency"],
        )

    def test_block_require_after_bom(self):
        content = (
            "\ufeffrequire (\n"
            "example.org/one v1.0.0\n"
            "example.org/two v2.0.0 // indirect\n"
            ")\n"
        )
        self.assertEqual(
            parse_go_requirements(content),
            ["example.org/one", "example.org/two"],
        )

    def test_bom_only_stripped_at_document_start(self):
        content = (
            "require example.org/first v1.0.0\n"
            "\ufeffrequire example.org/not-a-directive v1.0.0\n"
        )
        self.assertEqual(parse_go_requirements(content), ["example.org/first"])


if __name__ == "__main__":
    unittest.main()
