"""Julia Pkg.test discovery does not trust linked or unreadable test trees."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.julia_tests import _safe_test_tree, julia_test_command


class JuliaTestTreeSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'Project.toml').write_text('name = "TestProject"\n', encoding='utf-8')
        (self.root / 'test').mkdir()
        (self.root / 'test' / 'runtests.jl').write_text('using Test\n', encoding='utf-8')

    def plan(self):
        return julia_test_command(self.root, {'Project.toml'})

    def test_regular_nested_test_tree_is_supported(self):
        helpers = self.root / 'test' / 'helpers'
        helpers.mkdir()
        (helpers / 'fixture.jl').write_text('x = 1\n', encoding='utf-8')
        self.assertEqual(self.plan()['ecosystem'], 'Julia')

    def test_symlinked_helper_and_test_project_manifest_are_rejected(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'outside.jl'
            target.write_text('error("unexpected execution")\n', encoding='utf-8')
            for name in ('helper.jl', 'Project.toml'):
                with self.subTest(name=name):
                    link = self.root / 'test' / name
                    try:
                        link.symlink_to(target)
                    except (OSError, NotImplementedError):
                        self.skipTest('symlinks unavailable')
                    self.assertIsNone(self.plan())
                    link.unlink()

    def test_nested_directory_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as external:
            nested = self.root / 'test' / 'fixtures'
            try:
                nested.symlink_to(external, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(self.plan())

    def test_scandir_failure_returns_no_plan(self):
        with patch('devpilot.julia_tests.os.scandir', side_effect=PermissionError):
            self.assertIsNone(self.plan())

    def test_tree_entry_limit_fails_closed(self):
        for index in range(4097):
            (self.root / 'test' / f'fixture-{index:04}.jl').touch()
        self.assertFalse(_safe_test_tree(self.root / 'test'))
        self.assertIsNone(self.plan())


if __name__ == '__main__':
    unittest.main()
