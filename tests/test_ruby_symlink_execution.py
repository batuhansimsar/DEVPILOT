"""Ensure Ruby test execution respects symlink exclusions from discovery."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.ruby_tests import ruby_test_command


@unittest.skipUnless(shutil.which('ruby'), 'Ruby interpreter is not installed')
class RubySymlinkExecutionTests(unittest.TestCase):
    @staticmethod
    def run_loader(root: Path, script: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ['ruby', '-Itest', '-e', script], cwd=root,
            capture_output=True, text=True, check=False, timeout=15,
        )

    def test_loader_ignores_linked_tests_and_fails_without_regular_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / 'project'
            test_dir = root / 'test'
            test_dir.mkdir(parents=True)
            (test_dir / 'test_helper.rb').write_text('', encoding='utf-8')
            regular = test_dir / 'safe_test.rb'
            regular.write_text('File.write("safe_loaded", "yes")\n', encoding='utf-8')
            outside = base / 'external_test.rb'
            outside.write_text('File.write("outside_loaded", "yes")\n', encoding='utf-8')
            try:
                (test_dir / 'linked_test.rb').symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest('File symlinks are unsupported')

            command = ruby_test_command(root, {'Gemfile'})
            self.assertIsNotNone(command)
            script = command['argv'][5]

            first_run = self.run_loader(root, script)
            self.assertEqual(first_run.returncode, 0, first_run.stderr)
            self.assertTrue((root / 'safe_loaded').exists())
            self.assertFalse((root / 'outside_loaded').exists())

            # An approved, already-discovered command must not run only symlinks
            # after the filesystem changes between discovery and execution.
            regular.unlink()
            second_run = self.run_loader(root, script)
            self.assertNotEqual(second_run.returncode, 0)
            self.assertIn('No Ruby test files found', second_run.stderr)
            self.assertFalse((root / 'outside_loaded').exists())

    def test_loader_aborts_if_test_directory_becomes_a_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / 'project'
            tests = root / 'test'
            tests.mkdir(parents=True)
            (tests / 'test_helper.rb').write_text('', encoding='utf-8')
            (tests / 'safe_test.rb').write_text('', encoding='utf-8')
            command = ruby_test_command(root, {'Gemfile'})
            self.assertIsNotNone(command)

            # Another process can replace a test directory after dry-run.
            tests.rename(root / 'old_test')
            external = base / 'external'
            external.mkdir()
            (external / 'outside_test.rb').write_text(
                'File.write("outside_loaded", "yes")\n', encoding='utf-8',
            )
            try:
                tests.symlink_to(external, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('Directory symlinks are unsupported')

            result = self.run_loader(root, command['argv'][5])
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('No Ruby test files found', result.stderr)
            self.assertFalse((root / 'outside_loaded').exists())


if __name__ == '__main__':
    unittest.main()
