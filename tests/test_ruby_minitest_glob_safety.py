"""Regression tests for Ruby discovery/execution parity and symlink safety."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.ruby_tests import ruby_test_command


class RubyMinitestGlobSafetyTests(unittest.TestCase):
    def test_hidden_tests_are_not_mistaken_for_runnable_suites(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test' / '.hidden').mkdir(parents=True)
            (root / 'test' / 'test_helper.rb').write_text('')
            (root / 'test' / '.hidden_test.rb').write_text('')
            (root / 'test' / '.hidden' / 'private_test.rb').write_text('')
            self.assertIsNone(ruby_test_command(root, {'Gemfile'}))
            (root / 'test' / 'visible_test.rb').write_text('')
            self.assertIsNotNone(ruby_test_command(root, {'Gemfile'}))

    @unittest.skipUnless(shutil.which('ruby'), 'Ruby executable not available')
    def test_minitest_loader_does_not_execute_symlinked_test_files(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            tests = root / 'test'
            tests.mkdir()
            (tests / 'test_helper.rb').write_text('')
            (tests / 'safe_test.rb').write_text('puts "SAFE_TEST_RAN"\n')
            target = Path(external) / 'outside_test.rb'
            target.write_text('puts "OUTSIDE_TEST_RAN"\n')
            try:
                (tests / 'outside_test.rb').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks not available')

            command = ruby_test_command(root, {'Gemfile'})
            self.assertIsNotNone(command)
            completed = subprocess.run(
                ['ruby', '-Itest', '-e', command['argv'][-1]],
                cwd=root, capture_output=True, text=True, timeout=10, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn('SAFE_TEST_RAN', completed.stdout)
            self.assertNotIn('OUTSIDE_TEST_RAN', completed.stdout)

    @unittest.skipUnless(shutil.which('ruby'), 'Ruby executable not available')
    def test_loader_fails_instead_of_running_only_symlinked_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / 'test'
            tests.mkdir()
            (tests / 'test_helper.rb').write_text('')
            (tests / 'safe_test.rb').write_text('')
            command = ruby_test_command(root, {'Gemfile'})
            (tests / 'safe_test.rb').unlink()
            target = root / 'outside.rb'
            target.write_text('puts "OUTSIDE_TEST_RAN"\n')
            try:
                (tests / 'linked_test.rb').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks not available')
            completed = subprocess.run(
                ['ruby', '-Itest', '-e', command['argv'][-1]],
                cwd=root, capture_output=True, text=True, timeout=10, check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn('No Ruby test files found', completed.stderr)
            self.assertNotIn('OUTSIDE_TEST_RAN', completed.stdout)


if __name__ == '__main__':
    unittest.main()
