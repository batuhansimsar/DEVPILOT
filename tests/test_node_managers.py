"""Node test discovery uses the project's package manager without executing code."""
import json
import tempfile
import unittest
from pathlib import Path

from devpilot import core
from devpilot.node_manager import _node_test_manager


class NodePackageManagerTests(unittest.TestCase):
    def test_no_lockfile_uses_npm(self):
        self.assertEqual(_node_test_manager({}, set()), 'npm')

    def test_supported_lockfiles(self):
        cases = [
            ('package-lock.json', 'npm'), ('npm-shrinkwrap.json', 'npm'),
            ('pnpm-lock.yaml', 'pnpm'), ('yarn.lock', 'yarn'),
            ('bun.lock', 'bun'), ('bun.lockb', 'bun'),
        ]
        for name, expected in cases:
            with self.subTest(name=name):
                self.assertEqual(_node_test_manager({}, {name}), expected)

    def test_declared_manager_wins_over_lockfile(self):
        self.assertEqual(_node_test_manager({'packageManager': 'pnpm@9.5.0'}, {'yarn.lock'}), 'pnpm')
        self.assertEqual(_node_test_manager({'packageManager': 'yarn@4.6.0'}, set()), 'yarn')

    def test_conflicting_lockfiles_avoid_guessing(self):
        self.assertIsNone(_node_test_manager({}, {'package-lock.json', 'pnpm-lock.yaml'}))

    def test_duplicate_markers_for_same_manager_are_safe(self):
        self.assertEqual(_node_test_manager({}, {'bun.lock', 'bun.lockb'}), 'bun')

    def test_unknown_manager_uses_lockfile_evidence(self):
        self.assertEqual(_node_test_manager({'packageManager': 'other@1'}, {'yarn.lock'}), 'yarn')
        self.assertIsNone(_node_test_manager({'packageManager': 'other@1'}, {'yarn.lock', 'pnpm-lock.yaml'}))

    def test_discovered_test_commands_use_correct_manager(self):
        for marker, expected in (
            ('pnpm-lock.yaml', ['pnpm', 'test']),
            ('yarn.lock', ['yarn', 'test']),
            ('bun.lock', ['bun', 'run', 'test']),
        ):
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'package.json').write_text(json.dumps({'scripts': {'test': 'echo hello'}}))
                (root / marker).write_text('')
                commands = core.test_commands(root)
                self.assertEqual(commands[0]['argv'], expected)

    def test_conflicting_locks_warn_and_disable_node_test(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'package.json').write_text('{"scripts":{"test":"echo hello"}}')
            (root / 'yarn.lock').write_text('')
            (root / 'pnpm-lock.yaml').write_text('')
            self.assertEqual(core.test_commands(root), [])
            self.assertTrue(any('Conflicting Node.js lockfiles' in x for x in core.analyze_project(root)['problems']))

    def test_symlink_lockfile_is_not_considered(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            (root / 'package.json').write_text('{"scripts":{"test":"echo hello"}}')
            (root / 'package-lock.json').write_text('')
            try:
                (root / 'yarn.lock').symlink_to(Path(outside) / 'lock')
            except (OSError, NotImplementedError):
                self.skipTest('symlink support unavailable')
            self.assertEqual(core.test_commands(root)[0]['argv'], ['npm', 'test'])


if __name__ == '__main__':
    unittest.main()
