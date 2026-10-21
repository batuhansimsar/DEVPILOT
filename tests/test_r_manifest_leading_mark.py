"""RStudio manifest names must not start with terminal-spoofing marks."""

import unittest

from devpilot.r_manifests import is_r_manifest


class RManifestLeadingMarkTests(unittest.TestCase):
    def test_rejects_initial_combining_marks(self):
        for name in (
            '\u0301analysis.Rproj',  # Combining acute accent.
            '\u034fhidden.Rproj',  # Combining grapheme joiner.
            '\u093eproject.Rproj',  # Devanagari spacing mark.
            '\u20ddexperiment.Rproj',  # Enclosing circle mark.
        ):
            with self.subTest(name=ascii(name)):
                self.assertFalse(is_r_manifest(name))

    def test_allows_combining_marks_inside_internationalized_names(self):
        for name in ('Cafe\u0301.Rproj', 'हिन्दी.Rproj', 'normal.Rproj', 'renv.lock'):
            with self.subTest(name=ascii(name)):
                self.assertTrue(is_r_manifest(name))


if __name__ == '__main__':
    unittest.main()
