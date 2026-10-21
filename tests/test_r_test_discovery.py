"""Regression coverage for safe opt-in R testthat discovery."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.cli import main
from devpilot.core import test_commands
from devpilot.r_tests import r_test_command
from devpilot.test_selection import select_test_commands


class RTestDiscoveryTests(unittest.TestCase):
    def make_suite(self, root, marker='renv.lock'):
        (root / marker).touch()
        suite = root / 'tests' / 'testthat'
        suite.mkdir(parents=True)
        (suite / 'test-example.R').touch()
        return suite

    def test_rstudio_project_uses_test_dir(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_suite(root, 'analysis.Rproj')
            self.assertEqual(r_test_command(root, {'analysis.Rproj'})['argv'], [
                'Rscript', '-e', 'testthat::test_dir("tests/testthat")'])

    def test_package_uses_test_local(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_suite(root)
            (root / 'DESCRIPTION').write_text('Package: example\n', encoding='utf-8')
            self.assertEqual(r_test_command(root, {'renv.lock', 'DESCRIPTION'})['argv'], [
                'Rscript', '-e', 'testthat::test_local(".")'])

    def test_missing_marker_or_test_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            suite = self.make_suite(root)
            self.assertIsNone(r_test_command(root, {'DESCRIPTION'}))
            (suite / 'test-example.R').unlink()
            (suite / 'helper.R').touch()
            (suite / 'test-example.R.bak').touch()
            self.assertIsNone(r_test_command(root, {'renv.lock'}))

    def test_symlinked_test_path_and_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            (root / 'analysis.Rproj').touch()
            outside = Path(external)
            (outside / 'test-outside.R').touch()
            try:
                (root / 'tests').symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertIsNone(r_test_command(root, {'analysis.Rproj'}))
            (root / 'tests').unlink()
            suite = root / 'tests' / 'testthat'
            suite.mkdir(parents=True)
            (suite / 'test-outside.R').symlink_to(outside / 'test-outside.R')
            self.assertIsNone(r_test_command(root, {'analysis.Rproj'}))
            (root / 'analysis.Rproj').unlink()
            (root / 'analysis.Rproj').symlink_to(outside / 'test-outside.R')
            self.assertIsNone(r_test_command(root, {'analysis.Rproj'}))

    def test_invalid_filename_cannot_enable_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_suite(root)
            self.assertIsNone(r_test_command(root, {'bad\nname.Rproj'}))

    def test_cli_dry_run_and_explicit_yes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_suite(root)
            (root / 'go.mod').touch()
            self.assertEqual([c['ecosystem'] for c in
                              select_test_commands(test_commands(root), 'r')], ['R'])
            out = io.StringIO()
            with patch('devpilot.cli.command_result') as runner, contextlib.redirect_stdout(out):
                code = main(['test', '--path', directory, '--ecosystem', 'r', '--json'])
            self.assertEqual(code, 0)
            self.assertFalse(json.loads(out.getvalue())['executed'])
            runner.assert_not_called()

            out = io.StringIO()
            with patch('devpilot.cli.command_result', return_value={'exit_code': 0}) as runner, \
                    contextlib.redirect_stdout(out):
                code = main(['test', '--path', directory, '--ecosystem', 'r', '--yes', '--json'])
            self.assertEqual(code, 0)
            runner.assert_called_once()
            self.assertEqual(runner.call_args.args[0],
                             ['Rscript', '-e', 'testthat::test_dir("tests/testthat")'])
            self.assertTrue(json.loads(out.getvalue())['executed'])


if __name__ == '__main__':
    unittest.main()
