"""Regression coverage for safe PEP 751 pylock filename matching."""

import unittest

from devpilot.pylock import is_pylock_manifest


class PylockFilenameHardeningTests(unittest.TestCase):
    def test_standard_and_safe_named_lockfiles(self):
        for filename in ('pylock.toml', 'pylock.dev.toml',
                         'pylock.production_2.toml', 'pylock.Release-1.toml'):
            with self.subTest(filename=filename):
                self.assertTrue(is_pylock_manifest(filename))

    def test_rejects_invalid_filename_segments(self):
        for filename in ('pylock..toml', 'pylock.dev.extra.toml',
                         'pylock. dev.toml', 'pylock.dev .toml',
                         'pylock.a/b.toml', 'pylock.a\\b.toml',
                         'pylock.\x1b[31m.toml', 'pylock.dev\n.toml',
                         'pylock.🧪.toml', 'Pylock.dev.toml',
                         'pylock.dev.toml.bak'):
            with self.subTest(filename=filename):
                self.assertFalse(is_pylock_manifest(filename))

    def test_non_string_names_are_rejected(self):
        for filename in (None, b'pylock.toml', 0):
            with self.subTest(filename=filename):
                self.assertFalse(is_pylock_manifest(filename))


if __name__ == '__main__':
    unittest.main()
