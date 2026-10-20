import tempfile
import unittest
from pathlib import Path

from devpilot.node import package_manager


class PackageManagerTests(unittest.TestCase):
    def test_pnpm_lockfile(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'pnpm-lock.yaml').write_text('lockfileVersion: 9')
            self.assertEqual(package_manager(Path(d), {})[0], 'pnpm')

    def test_package_manager_declaration_overrides_lockfile(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'package-lock.json').write_text('{}')
            self.assertEqual(package_manager(Path(d), {'packageManager': 'yarn@4.5.0'})[0], 'yarn')

    def test_conflicting_lockfiles_fall_back_to_npm(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'pnpm-lock.yaml').touch()
            (Path(d) / 'yarn.lock').touch()
            self.assertEqual(package_manager(Path(d), {}), ('npm', ['pnpm-lock.yaml', 'yarn.lock'], None))

    def test_bun_lockfile(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'bun.lockb').touch()
            self.assertEqual(package_manager(Path(d), {})[0], 'bun')

    def test_symlink_lockfile_ignored(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'lock'
            target.touch()
            try:
                (Path(d) / 'yarn.lock').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unsupported')
            self.assertEqual(package_manager(Path(d), {})[0], 'npm')

    def test_invalid_package_manager_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'pnpm-lock.yaml').touch()
            self.assertEqual(package_manager(Path(d), {'packageManager': 'hijack@1'})[0], 'pnpm')


    def test_pnpm_workspace_without_lockfile(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'pnpm-workspace.yaml').write_text('packages:\\n  - packages/*\\n')
            self.assertEqual(package_manager(Path(d), {}), ('pnpm', [], None))

    def test_pnpm_workspace_does_not_override_explicit_manager(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'pnpm-workspace.yaml').touch()
            self.assertEqual(package_manager(Path(d), {'packageManager': 'yarn@4.5.0'})[0], 'yarn')

    def test_pnpm_workspace_does_not_override_lockfiles(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'pnpm-workspace.yaml').touch()
            (Path(d) / 'package-lock.json').touch()
            self.assertEqual(package_manager(Path(d), {})[0], 'npm')

    def test_pnpm_workspace_symlink_ignored(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'workspace.yaml'
            target.touch()
            try:
                (Path(d) / 'pnpm-workspace.yaml').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unsupported')
            self.assertEqual(package_manager(Path(d), {}), ('npm', [], None))



if __name__ == '__main__':
    unittest.main()
