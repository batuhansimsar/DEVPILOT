"""Test inventory must inspect the whole bounded tree before approving a runner."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.ruby_tests import _has_test_file, ruby_test_command


class RubyCompleteTestScanTests(unittest.TestCase):
    def test_late_excess_entries_reject_early_matching_test(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            suite = root / 'test'
            suite.mkdir()
            (suite / 'test_helper.rb').touch()
            (suite / 'safe_test.rb').touch()
            for index in range(4):
                (suite / f'fixture_{index}.txt').touch()
            real_iterdir = Path.iterdir

            def ordered(path):
                if path == suite:
                    # A valid test appears before the oversized tail.
                    return iter([suite / 'safe_test.rb', suite / 'test_helper.rb',
                                 *[suite / f'fixture_{index}.txt' for index in range(4)]])
                return real_iterdir(path)

            with patch.object(Path, 'iterdir', ordered), patch('devpilot.ruby_tests._MAX_DISCOVERY_ENTRIES', 3):
                self.assertFalse(_has_test_file(suite, '_test.rb', skip_hidden=True))
                self.assertIsNone(ruby_test_command(root, {'Gemfile'}))

    def test_regular_minitest_suite_still_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            suite = root / 'test'
            suite.mkdir()
            (suite / 'test_helper.rb').touch()
            (suite / 'safe_test.rb').touch()
            (suite / 'data.txt').touch()
            self.assertIsNotNone(ruby_test_command(root, {'Gemfile'}))

    def test_unreadable_subdirectory_after_matching_test_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'safe_test.rb').touch()
            nested = root / 'nested'
            nested.mkdir()
            original = Path.iterdir

            def iterator(path):
                if path == root:
                    return iter([root / 'safe_test.rb', nested])
                if path == nested:
                    raise OSError('private details must not escape')
                return original(path)

            with patch.object(Path, 'iterdir', iterator):
                self.assertFalse(_has_test_file(root, '_test.rb'))


if __name__ == '__main__':
    unittest.main()
