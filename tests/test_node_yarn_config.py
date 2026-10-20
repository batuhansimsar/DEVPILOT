"""A Yarn configuration identifies new projects even before a lockfile exists."""

import tempfile
import unittest
from pathlib import Path

from devpilot.node import package_manager


class YarnConfigDetectionTests(unittest.TestCase):
    def test_yarn_config_without_lockfile(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / '.yarnrc.yml').write_text('nodeLinker: node-modules\n')
            self.assertEqual(package_manager(root, {}), ('yarn', [], None))

    def test_explicit_manager_and_lockfile_override_yarn_config(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / '.yarnrc.yml').touch()
            self.assertEqual(package_manager(root, {'packageManager': 'bun@1.0.0'})[0], 'bun')
            (root / 'package-lock.json').touch()
            self.assertEqual(package_manager(root, {})[0], 'npm')

    def test_symlinked_yarn_config_is_ignored(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
            root = Path(d)
            target = Path(outside) / 'config'
            target.write_text('nodeLinker: node-modules\n')
            try:
                (root / '.yarnrc.yml').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertEqual(package_manager(root, {}), ('npm', [], None))

    def test_pnpm_workspace_takes_precedence_over_yarn_config(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / '.yarnrc.yml').touch()
            (root / 'pnpm-workspace.yaml').touch()
            self.assertEqual(package_manager(root, {})[0], 'pnpm')


if __name__ == '__main__':
    unittest.main()
