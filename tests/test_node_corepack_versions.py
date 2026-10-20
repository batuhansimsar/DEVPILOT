"""Corepack packageManager must be a fixed, syntactically valid version."""

import tempfile
import unittest
from pathlib import Path

from devpilot.node import package_manager


class CorepackVersionTests(unittest.TestCase):
    def test_invalid_versions_cannot_override_a_lockfile(self):
        invalid = (
            'pnpm@latest', 'pnpm@^9.0.0', 'pnpm@9', 'pnpm@9.0',
            'pnpm@9.0.0/../../malicious', 'pnpm@9.0.0@other',
            'pnpm@https://example.invalid/manager', 'pnpm@9.0.0#comment',
            'pnpm@01.2.3', 'pnpm@9.0.0-rc..1',
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'yarn.lock').touch()
            for metadata in invalid:
                with self.subTest(packageManager=metadata):
                    self.assertEqual(package_manager(root, {'packageManager': metadata}),
                                     ('yarn', ['yarn.lock'], None))

    def test_valid_fixed_versions_still_override_lockfiles(self):
        valid = (
            'pnpm@9.0.0', 'pnpm@9.1.0-rc.2',
            'pnpm@9.0.0+sha512.abc123', 'pnpm@9.0.0+sha512.abcd==',
            'pnpm@10.0.0+build.1',
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'yarn.lock').touch()
            for metadata in valid:
                with self.subTest(packageManager=metadata):
                    self.assertEqual(package_manager(root, {'packageManager': metadata}),
                                     ('pnpm', ['yarn.lock'], 'pnpm'))


if __name__ == '__main__':
    unittest.main()
