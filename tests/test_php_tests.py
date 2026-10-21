import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.php_tests import php_test_command


class PHPUnitDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'composer.json').write_text('{}', encoding='utf-8')

    def discover(self, names=None):
        return php_test_command(self.root, {'composer.json'} if names is None else names)

    def test_configured_suite_prefers_phpunit_xml(self):
        (self.root / 'phpunit.xml').touch()
        (self.root / 'phpunit.xml.dist').touch()
        self.assertEqual(self.discover({'composer.json', 'phpunit.xml', 'phpunit.xml.dist'}), {
            'ecosystem': 'PHP',
            'argv': ['php', 'vendor/bin/phpunit', '--configuration', 'phpunit.xml'],
            'reason': 'Composer project with phpunit.xml',
        })

    def test_dist_config_only(self):
        (self.root / 'phpunit.xml.dist').touch()
        self.assertEqual(self.discover({'composer.json', 'phpunit.xml.dist'})['argv'][-1], 'phpunit.xml.dist')

    def test_conventional_nested_tests(self):
        nested = self.root / 'tests' / 'Unit'
        nested.mkdir(parents=True)
        (nested / 'ExampleTest.php').touch()
        self.assertEqual(self.discover()['argv'], ['php', 'vendor/bin/phpunit', 'tests'])

    def test_no_test_suite_is_not_reported(self):
        (self.root / 'tests').mkdir()
        (self.root / 'tests' / 'Helper.php').touch()
        self.assertIsNone(self.discover())

    def test_missing_composer_marker_is_not_reported(self):
        (self.root / 'phpunit.xml').touch()
        self.assertIsNone(self.discover({'phpunit.xml'}))

    def test_symlinked_config_and_manifest_are_rejected(self):
        (self.root / 'phpunit.xml').touch()
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'external'
            target.touch()
            for name in ('composer.json', 'phpunit.xml'):
                file = self.root / name
                file.unlink()
                try:
                    file.symlink_to(target)
                except (OSError, NotImplementedError):
                    self.skipTest('File symlinks unavailable')
                self.assertIsNone(self.discover({'composer.json', 'phpunit.xml'}))
                file.unlink()
                file.touch()

    def test_linked_test_entry_is_not_evidence(self):
        tests = self.root / 'tests'
        tests.mkdir()
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'ExternalTest.php'
            target.touch()
            try:
                (tests / 'ExternalTest.php').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('File symlinks unavailable')
            self.assertIsNone(self.discover())

    def test_unreadable_directory_is_inconclusive(self):
        (self.root / 'tests').mkdir()
        with patch.object(Path, 'iterdir', side_effect=OSError('permission denied')):
            self.assertIsNone(self.discover())


class PHPUnitCLIIntegrationTests(unittest.TestCase):
    def test_project_detection_and_opt_in_php_execution(self):
        import contextlib
        import io
        import json
        from devpilot.cli import main
        from devpilot.core import detect_projects

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'composer.json').write_text('{}', encoding='utf-8')
            (root / 'phpunit.xml.dist').touch()
            self.assertIn('PHP', detect_projects(root))
            output = io.StringIO()
            with patch('devpilot.cli.command_result') as runner, contextlib.redirect_stdout(output):
                status = main(['test', '--path', directory, '--ecosystem', 'php', '--json'])
                runner.assert_not_called()
            self.assertEqual(status, 0)
            report = json.loads(output.getvalue())
            self.assertFalse(report['executed'])
            self.assertEqual([item['ecosystem'] for item in report['commands']], ['PHP'])

            output = io.StringIO()
            with patch('devpilot.cli.command_result', return_value={'exit_code': 0}) as runner, contextlib.redirect_stdout(output):
                status = main(['test', '--path', directory, '--ecosystem', 'php', '--yes', '--json'])
            self.assertEqual(status, 0)
            runner.assert_called_once_with(
                ['php', 'vendor/bin/phpunit', '--configuration', 'phpunit.xml.dist'], root.resolve(), 120
            )
            self.assertTrue(json.loads(output.getvalue())['executed'])
