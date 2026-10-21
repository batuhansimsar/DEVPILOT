"""R testthat discovery is explicit, conservative and symlink-safe."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.r_tests import r_test_command


class RTestCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'analysis.Rproj').touch()
        (self.root / 'DESCRIPTION').write_text('Package: example\n', encoding='utf-8')
        self.tests = self.root / 'tests'
        self.suite = self.tests / 'testthat'
        self.suite.mkdir(parents=True)
        (self.tests / 'testthat.R').touch()
        (self.suite / 'test-basic.R').touch()

    def discover(self, names=None):
        return r_test_command(self.root, {'analysis.Rproj'} if names is None else names)

    def test_standard_testthat_package(self):
        self.assertEqual(self.discover(), {
            'ecosystem': 'R',
            'argv': ['Rscript', '-e', 'testthat::test_local()'],
            'reason': 'R package with testthat entry point and tests',
        })

    def test_renv_lockfile_also_authorizes_discovery(self):
        (self.root / 'renv.lock').touch()
        self.assertIsNotNone(self.discover({'renv.lock'}))

    def test_missing_or_unverified_project_markers_are_rejected(self):
        self.assertIsNone(self.discover({'DESCRIPTION'}))
        self.assertIsNone(self.discover({'phantom.Rproj'}))
        self.assertIsNone(self.discover({'analysis.Rproj.bak'}))
        (self.root / 'analysis.Rproj').unlink()
        self.assertIsNone(self.discover())

    def test_require_real_package_and_suite_files(self):
        for path in (self.root / 'DESCRIPTION', self.tests / 'testthat.R', self.suite / 'test-basic.R'):
            with self.subTest(path=path.name):
                path.unlink()
                self.assertIsNone(self.discover())
                path.touch()
                if path.name == 'DESCRIPTION':
                    path.write_text('Package: example\n', encoding='utf-8')

    def test_no_matching_test_files(self):
        (self.suite / 'test-basic.R').unlink()
        (self.suite / 'helper.R').touch()
        (self.suite / 'test-data.r.bak').touch()
        (self.suite / 'test-ignored.R.bak').touch()
        self.assertIsNone(self.discover())

    def test_symlinked_markers_and_test_files_rejected(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'linked'
            target.touch()
            for path in (self.root / 'analysis.Rproj', self.root / 'DESCRIPTION',
                         self.tests / 'testthat.R', self.suite / 'test-basic.R'):
                with self.subTest(path=path.name):
                    path.unlink()
                    try:
                        path.symlink_to(target)
                    except (OSError, NotImplementedError):
                        self.skipTest('File symlinks unavailable')
                    self.assertIsNone(self.discover())
                    path.unlink()
                    path.touch()
                if path.name == 'DESCRIPTION':
                    path.write_text('Package: example\n', encoding='utf-8')

    def test_symlinked_suite_and_tests_directory_rejected(self):
        import shutil
        with tempfile.TemporaryDirectory() as external:
            for path in (self.suite, self.tests):
                with self.subTest(path=path.name):
                    shutil.rmtree(path)
                    try:
                        path.symlink_to(external, target_is_directory=True)
                    except (OSError, NotImplementedError):
                        self.skipTest('Directory symlinks unavailable')
                    self.assertIsNone(self.discover())
                    path.unlink()
                    self.suite.mkdir(parents=True, exist_ok=True)
                    (self.tests / 'testthat.R').touch()
                    (self.suite / 'test-basic.R').touch()


class RTestCLIIntegrationTests(unittest.TestCase):
    def test_r_dry_run_does_not_execute_project_code(self):
        from devpilot.cli import main
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'project.Rproj').touch()
            (root / 'DESCRIPTION').write_text('Package: example\n', encoding='utf-8')
            (root / 'tests' / 'testthat').mkdir(parents=True)
            (root / 'tests' / 'testthat.R').touch()
            (root / 'tests' / 'testthat' / 'test-example.R').touch()
            (root / 'go.mod').touch()
            out = io.StringIO()
            with patch('devpilot.cli.command_result') as run, contextlib.redirect_stdout(out):
                status = main(['test', '--path', directory, '--ecosystem', 'r', '--json'])
                run.assert_not_called()
            data = json.loads(out.getvalue())
            self.assertEqual(status, 0)
            self.assertFalse(data['executed'])
            self.assertEqual([x['ecosystem'] for x in data['commands']], ['R'])

    def test_yes_executes_only_selected_r_command(self):
        from devpilot.cli import main
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'renv.lock').touch()
            (root / 'DESCRIPTION').write_text('Package: example\n', encoding='utf-8')
            (root / 'tests' / 'testthat').mkdir(parents=True)
            (root / 'tests' / 'testthat.R').touch()
            (root / 'tests' / 'testthat' / 'test-feature.R').touch()
            out = io.StringIO()
            with patch('devpilot.cli.command_result', return_value={'exit_code': 0}) as run, contextlib.redirect_stdout(out):
                status = main(['test', '--path', directory, '--ecosystem', 'r', '--yes', '--json'])
            self.assertEqual(status, 0)
            self.assertTrue(json.loads(out.getvalue())['executed'])
            run.assert_called_once_with(['Rscript', '-e', 'testthat::test_local()'], root.resolve(), 120)


if __name__ == '__main__':
    unittest.main()
