"""Root pytest arguments must not widen collection beyond detected files."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.python_test_targets import root_pytest_targets


class RootPytestTargetsTests(unittest.TestCase):
    def test_collect_only_root_test_modules(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'test_feature.py').touch()
            (root / 'feature_test.py').touch()
            other = root / 'src'
            other.mkdir()
            (other / 'test_other.py').touch()
            self.assertEqual(root_pytest_targets(root, 100),
                             ['./feature_test.py', './test_feature.py'])

    def test_unsafe_root_symlink_and_entry_limit_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'test_feature.py').touch()
            self.assertIsNone(root_pytest_targets(root, 0))
            try:
                (root / 'linked').symlink_to(root / 'test_feature.py')
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertIsNone(root_pytest_targets(root, 100))

    def test_root_pytest_ignores_nested_external_tests(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as outside:
            root = Path(folder)
            (root / 'test_safe.py').write_text('def test_ok(): assert True\n')
            (Path(outside) / 'test_external.py').write_text('def test_outside(): assert False\n')
            nested = root / 'nested'
            nested.mkdir()
            try:
                (nested / 'linked').symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('directory symlinks unavailable')
            targets = root_pytest_targets(root, 100)
            self.assertEqual(targets, ['./test_safe.py'])
            result = subprocess.run([sys.executable, '-m', 'pytest', '-q', *targets],
                                    cwd=root, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn('test_external', result.stdout + result.stderr)

    def test_filename_cannot_be_interpreted_as_option(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / '--danger_test.py').touch()
            self.assertEqual(root_pytest_targets(root, 5), ['./--danger_test.py'])

    def test_empty_and_nontest_files_are_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'feature.py').touch()
            self.assertEqual(root_pytest_targets(root, 10), [])

    def test_unreadable_tree_returns_none(self):
        with patch('pathlib.Path.iterdir', side_effect=OSError('private path')):
            self.assertIsNone(root_pytest_targets(Path('/private'), 100))


if __name__ == '__main__':
    unittest.main()
