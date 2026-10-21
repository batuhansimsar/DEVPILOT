"""Ensure only physical line endings split pip requirement declarations."""

import unittest

from devpilot.requirements_deps import parse_requirements_dependencies


class RequirementsPhysicalLineTests(unittest.TestCase):
    def test_unicode_separators_cannot_create_dependencies_in_comments(self):
        for separator in ("\u0085", "\u2028", "\u2029", "\x0b", "\x0c"):
            with self.subTest(separator=repr(separator)):
                source = "# ignored" + separator + "phantom==1\nreal==2\n"
                self.assertEqual(parse_requirements_dependencies(source), ["real"])

    def test_unicode_separators_cannot_split_invalid_declarations(self):
        source = "invalid!!!\u2028phantom==1\nreal==2\n"
        self.assertEqual(parse_requirements_dependencies(source), ["real"])

    def test_standard_cr_lf_and_crlf_are_all_supported(self):
        source = "first==1\rsecond==2\r\nthird==3\n"
        self.assertEqual(
            parse_requirements_dependencies(source),
            ["first", "second", "third"],
        )


if __name__ == "__main__":
    unittest.main()
