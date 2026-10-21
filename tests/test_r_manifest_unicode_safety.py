"""RStudio project manifest detection rejects invisible Unicode spoofing."""

import unittest

from devpilot.r_manifests import is_r_manifest


class RManifestUnicodeSafetyTests(unittest.TestCase):
    def test_rejects_bidi_controls_and_invisible_formatting(self):
        for name in (
            'project\u202eexe.Rproj',  # Right-to-left override
            'project\u2066name.Rproj',  # Left-to-right isolate
            'project\u061cname.Rproj',  # Arabic letter mark
            'project\u200bname.Rproj',  # Zero-width space
            'project\u0085name.Rproj',  # C1 next-line control
            'project\udcffname.Rproj',  # Surrogate-escaped invalid filename byte
        ):
            with self.subTest(name=ascii(name)):
                self.assertFalse(is_r_manifest(name))

    def test_printable_international_names_and_lockfiles_remain_supported(self):
        for name in ('Révision 2026.Rproj', '数据分析.Rproj', 'analysis.Rproj', 'renv.lock'):
            with self.subTest(name=name):
                self.assertTrue(is_r_manifest(name))

    def test_path_segments_and_backups_still_rejected(self):
        for name in ('../project.Rproj', 'folder\\project.Rproj', 'project.Rproj~', '.hidden.Rproj'):
            with self.subTest(name=name):
                self.assertFalse(is_r_manifest(name))


if __name__ == '__main__':
    unittest.main()
