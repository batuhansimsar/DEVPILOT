"""Corepack packageManager SemVer prerelease validation regressions."""

import tempfile
import unittest
from pathlib import Path

from devpilot.node import package_manager


class NodeSemverPrereleaseTests(unittest.TestCase):
    def test_invalid_numeric_prerelease_falls_back_to_lockfile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'package-lock.json').write_text('{}')
            for prerelease in ('01', '0.09', 'alpha.02', '001.beta'):
                with self.subTest(prerelease=prerelease):
                    selected, locks, declared = package_manager(
                        root, {'packageManager': f'pnpm@1.2.3-{prerelease}'}
                    )
                    self.assertEqual((selected, declared), ('npm', None))
                    self.assertEqual(locks, ['package-lock.json'])

    def test_valid_alphanumeric_prereleases_still_select_declared_manager(self):
        with tempfile.TemporaryDirectory() as tmp:
            for pre in ('0', 'alpha.0', 'beta.01a', 'rc-01', 'alpha.0+build.01'):
                with self.subTest(pre=pre):
                    selected, _, declared = package_manager(
                        Path(tmp), {'packageManager': f'pnpm@1.2.3-{pre}'}
                    )
                    self.assertEqual((selected, declared), ('pnpm', 'pnpm'))


if __name__ == '__main__':
    unittest.main()
