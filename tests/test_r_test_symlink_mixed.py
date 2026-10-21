"""Reject mixed local and symlinked testthat suites before execution."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.r_tests import r_test_command


class MixedRTestSymlinkTests(unittest.TestCase):
    def test_valid_package_suite_never_executes_during_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'renv.lock').touch()
            (root / 'DESCRIPTION').write_text('Package: sample\n', encoding='utf-8')
            tests = root / 'tests'
            tests.mkdir()
            (tests / 'testthat.R').touch()
            suite = tests / 'testthat'
            suite.mkdir()
            (suite / 'test-local.R').touch()
            with patch('subprocess.run') as run:
                plan = r_test_command(root, {'renv.lock'})
            run.assert_not_called()
            self.assertEqual(plan['argv'], ['Rscript', '-e', 'testthat::test_local()'])

    def test_mixed_regular_and_linked_tests_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            (root / 'renv.lock').touch()
            (root / 'DESCRIPTION').write_text('Package: sample\n', encoding='utf-8')
            tests = root / 'tests'
            tests.mkdir()
            (tests / 'testthat.R').touch()
            suite = tests / 'testthat'
            suite.mkdir()
            (suite / 'test-local.R').touch()
            linked = suite / 'test-external.R'
            try:
                linked.symlink_to(Path(outside) / 'external.R')
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            # A valid local test must not mask an untrusted linked test file.
            self.assertIsNone(r_test_command(root, {'renv.lock'}))
            linked.unlink()
            self.assertIsNotNone(r_test_command(root, {'renv.lock'}))


if __name__ == '__main__':
    unittest.main()
