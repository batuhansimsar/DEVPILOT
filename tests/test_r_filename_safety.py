import unittest
from devpilot.r_manifests import is_r_manifest


class RManifestFilenameSafetyTests(unittest.TestCase):
    def test_rejects_invisible_or_directional_unicode(self):
        for marker in ('\u202e', '\u2028', '\u2029', '\u200b', '\u2066', '\u0085', '\ud800'):
            with self.subTest(marker=ascii(marker)):
                self.assertFalse(is_r_manifest(f'my{marker}project.Rproj'))

    def test_preserves_printable_names_and_lockfile(self):
        for filename in ('renv.lock', 'Project.Rproj', 'Research 2026.Rproj', 'École.Rproj', '分析.Rproj'):
            with self.subTest(filename=filename):
                self.assertTrue(is_r_manifest(filename))

    def test_ignores_other_invalid_manifests(self):
        for filename in ('hidden/.project.Rproj', 'foo\\bar.Rproj', '.hidden.Rproj', 'foo.Rproj.bak', None):
            with self.subTest(filename=filename):
                self.assertFalse(is_r_manifest(filename))


if __name__ == '__main__':
    unittest.main()
