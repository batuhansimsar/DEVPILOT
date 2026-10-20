import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot import core
from devpilot.cli import main


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name, content=''):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

    def test_analyze_detects_languages_and_manifests(self):
        self.write('package.json', json.dumps({'scripts': {'test': 'node test.js', 'dev': 'vite'}}))
        self.write('src/index.ts', 'let x = 1')
        self.write('src/component.tsx', '')
        self.write('.github/workflows/test.yml', '')
        result = core.analyze_project(self.root)
        self.assertEqual(result['project_types'], ['Node.js'])
        self.assertEqual(result['languages'], {'TypeScript': 2})
        self.assertEqual(result['npm_scripts'], ['dev', 'test'])
        self.assertIn('.github/workflows/test.yml', result['key_files'])

    def test_malformed_and_oversized_package_manifest(self):
        self.write('package.json', '{oops')
        self.assertTrue(core.analyze_project(self.root)['problems'])
        self.write('package.json', ' ' * (core.MAX_MANIFEST_BYTES + 1))
        self.assertIn('inspection limit', core.analyze_project(self.root)['problems'][0])

    def test_symlink_not_followed(self):
        with tempfile.TemporaryDirectory() as other:
            (Path(other) / 'secret.py').write_text('secret')
            try:
                (self.root / 'outside').symlink_to(other, target_is_directory=True)
                (self.root / 'link.py').symlink_to(Path(other) / 'secret.py')
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            self.assertEqual(core.analyze_project(self.root)['file_count'], 0)

    def test_ignores_dependency_dirs(self):
        self.write('node_modules/p.py')
        self.write('src/app.py')
        self.assertEqual(core.analyze_project(self.root)['languages'], {'Python': 1})

    def test_package_script_discovered_not_executed(self):
        self.write('package.json', '{"scripts": {"test": "echo tested"}}')
        cmds = core.test_commands(self.root)
        self.assertEqual(cmds[0]['argv'], ['npm', 'test'])
        with patch('devpilot.cli.command_result', side_effect=AssertionError('must not run')):
            self.assertEqual(main(['test', '--path', str(self.root)]), 0)

    def test_node_uses_installed_package_manager_lockfile(self):
        choices = {
            'pnpm-lock.yaml': ['pnpm', 'test'],
            'yarn.lock': ['yarn', 'test'],
            'bun.lock': ['bun', 'run', 'test'],
            'bun.lockb': ['bun', 'run', 'test'],
            'npm-shrinkwrap.json': ['npm', 'test'],
            'package-lock.json': ['npm', 'test'],
        }
        for filename, expected in choices.items():
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'package.json').write_text('{"scripts":{"test":"node tests.js"}}')
                (root / filename).touch()
                self.assertEqual(core.test_commands(root)[0]['argv'], expected)

    def test_node_package_manager_field_overrides_lockfiles(self):
        self.write('package.json', '{"packageManager":"pnpm@10.0.0","scripts":{"test":"node tests.js"}}')
        self.write('yarn.lock')
        self.assertEqual(core.test_commands(self.root)[0]['argv'], ['pnpm', 'test'])

    def test_node_unknown_package_manager_falls_back_to_npm(self):
        self.write('package.json', '{"packageManager":"untrusted@1.0","scripts":{"test":"node tests.js"}}')
        self.assertEqual(core.test_commands(self.root)[0]['argv'], ['npm', 'test'])

    def test_node_bun_package_manager_runs_script_not_native_tests(self):
        self.write('package.json', '{"packageManager":"bun@1.2.0","scripts":{"test":"custom-command"}}')
        self.assertEqual(core.test_commands(self.root)[0]['argv'], ['bun', 'run', 'test'])

    def test_node_symlinked_lockfile_not_trusted(self):
        self.write('package.json', '{"scripts":{"test":"node tests.js"}}')
        try:
            (self.root / 'pnpm-lock.yaml').symlink_to('missing-file')
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.assertEqual(core.test_commands(self.root)[0]['argv'], ['npm', 'test'])

    def test_python_test_detection(self):
        self.write('pyproject.toml')
        self.write('tests/test_demo.py')
        self.assertTrue(any(x['ecosystem'] == 'Python' for x in core.test_commands(self.root)))

    def test_doctor_missing_runtime_warns(self):
        self.write('go.mod', 'module sample')
        with patch('devpilot.core.shutil.which', return_value=None):
            report = core.doctor_report(self.root)
        self.assertFalse(report['ok'])
        self.assertIn('Go', report['project_types'])
        self.assertIn('Missing go required by detected project', report['warnings'])

    def test_tool_exit_and_timeout(self):
        result = core.command_result(['this-binary-does-not-exist-1234'], self.root)
        self.assertIsNone(result['exit_code'])
        self.assertIn('error', result)
        result = core.command_result(['python', '-c', 'import time; time.sleep(1)'], self.root, timeout=0.01)
        self.assertIsNone(result['exit_code'])

    def test_tcp_check_reachable(self):
        server = socket.socket()
        server.bind(('127.0.0.1', 0))
        server.listen()
        self.addCleanup(server.close)
        port = server.getsockname()[1]
        self.assertTrue(core.tcp_check('127.0.0.1', port, 1)['reachable'])

    def test_npm_test_with_wrong_type_ignored(self):
        self.write('package.json', '{"scripts": {"test": 42}}')
        self.assertEqual(core.test_commands(self.root), [])


if __name__ == '__main__':
    unittest.main()
