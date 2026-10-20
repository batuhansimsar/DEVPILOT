import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.core import doctor_report, test_commands


class NodeIntegrationTests(unittest.TestCase):
    def test_pnpm_test_command_from_lockfile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'package.json').write_text('{"scripts":{"test":"vitest"}}')
            (root / 'pnpm-lock.yaml').touch()
            self.assertEqual(test_commands(root)[0]['argv'], ['pnpm', 'test'])

    def test_ambiguous_lockfiles_warn_and_do_not_guess_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'package.json').write_text('{"scripts":{"test":"vitest"}}')
            (root / 'pnpm-lock.yaml').touch()
            (root / 'yarn.lock').touch()
            self.assertEqual(test_commands(root), [])
            with patch('devpilot.core.shutil.which', return_value='/bin/true'):
                report = doctor_report(root)
            self.assertFalse(report['ok'])
            self.assertTrue(any('Conflicting JavaScript lockfiles' in item for item in report['warnings']))

    def test_explicit_manager_allows_command_but_reports_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'package.json').write_text('{"packageManager":"yarn@4.0.0","scripts":{"test":"vitest"}}')
            (root / 'package-lock.json').touch()
            self.assertEqual(test_commands(root)[0]['argv'], ['yarn', 'test'])
            with patch('devpilot.core.shutil.which', return_value='/bin/true'):
                report = doctor_report(root)
            self.assertFalse(report['ok'])
            self.assertTrue(any('packageManager specifies yarn' in item for item in report['warnings']))


if __name__ == '__main__':
    unittest.main()
