"""Regression tests for Node package-manager selection and ambiguity."""
import json
import tempfile
import unittest
from pathlib import Path

from devpilot import core
from devpilot.node import package_manager


class NodePackageManagerTests(unittest.TestCase):
    def make_project(self, root: Path, manager=None, lockfiles=()):
        package = {'scripts': {'test': 'echo hello'}}
        if manager is not None:
            package['packageManager'] = manager
        (root / 'package.json').write_text(json.dumps(package), encoding='utf-8')
        for name in lockfiles:
            (root / name).write_text('', encoding='utf-8')
        return package

    def test_default_npm(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            self.assertEqual(core.test_commands(root)[0]['argv'], ['npm', 'test'])

    def test_lockfile_runners(self):
        for marker, expected in (
            ('package-lock.json', ['npm', 'test']),
            ('npm-shrinkwrap.json', ['npm', 'test']),
            ('pnpm-lock.yaml', ['pnpm', 'test']),
            ('yarn.lock', ['yarn', 'test']),
            ('bun.lock', ['bun', 'run', 'test']),
            ('bun.lockb', ['bun', 'run', 'test']),
        ):
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_project(root, lockfiles=(marker,))
                self.assertEqual(core.test_commands(root)[0]['argv'], expected)

    def test_explicit_manager_takes_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = self.make_project(root, manager='pnpm@9.5.0', lockfiles=('yarn.lock',))
            self.assertEqual(package_manager(root, package)[0], 'pnpm')
            self.assertEqual(core.test_commands(root)[0]['argv'], ['pnpm', 'test'])

    def test_conflicting_lockfiles_are_diagnostic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root, lockfiles=('yarn.lock', 'pnpm-lock.yaml'))
            self.assertEqual(core.test_commands(root), [])
            report = core.analyze_project(root)
            self.assertTrue(any('Conflicting Node.js lockfiles' in warning for warning in report['problems']))
            self.assertFalse(core.doctor_report(root)['ok'])

    def test_two_bun_lockfiles_do_not_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root, lockfiles=('bun.lock', 'bun.lockb'))
            self.assertEqual(core.test_commands(root)[0]['argv'], ['bun', 'run', 'test'])
            self.assertFalse(core.analyze_project(root)['problems'])

    def test_symlinked_lockfile_is_ignored(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            self.make_project(root, lockfiles=('package-lock.json',))
            try:
                (root / 'yarn.lock').symlink_to(Path(outside) / 'lock')
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertEqual(core.test_commands(root)[0]['argv'], ['npm', 'test'])
            self.assertFalse(core.analyze_project(root)['problems'])


if __name__ == '__main__':
    unittest.main()
