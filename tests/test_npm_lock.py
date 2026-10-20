"""Regression tests for privacy-safe npm package lock inventory."""

import json
import tempfile
import unittest
from pathlib import Path

from devpilot.npm_lock import parse_npm_lock
from devpilot.deps import scan
from devpilot.workspaces import discover_workspaces


class NpmLockTests(unittest.TestCase):
    def test_v3_installed_package_names_and_workspace_exclusion(self):
        content = json.dumps({
            'lockfileVersion': 3,
            'packages': {
                '': {'name': 'private-root', 'resolved': 'https://user:secret@host/root'},
                'packages/frontend': {'name': 'workspace-app'},
                'node_modules/react': {'version': '18.2.0', 'integrity': 'secret'},
                'node_modules/@scope/ui': {'resolved': 'https://token@private.invalid/pkg'},
                'node_modules/react/node_modules/scheduler': {'version': '0.23.0'},
            },
        })
        self.assertEqual(parse_npm_lock(content), ['@scope/ui', 'react', 'scheduler'])
        self.assertNotIn('secret', str(parse_npm_lock(content)))

    def test_v1_nested_dependencies(self):
        content = json.dumps({'lockfileVersion': 1, 'dependencies': {
            'react': {'version': '18', 'dependencies': {
                'scheduler': {'version': '0.23', 'resolved': 'https://secret@host/pkg'}}},
            '@types/node': {'version': '22'},
        }})
        self.assertEqual(parse_npm_lock(content), ['@types/node', 'react', 'scheduler'])

    def test_rejects_malformed_package_records_and_unsafe_names(self):
        cases = [
            '{"packages": {"node_modules/foo": {}, "node_modules/foo": {}}}',
            '{"packages": {"node_modules/good": true}}',
            '{"packages": {"node_modules/@scope/secret/extra": {}}}',
            '{"dependencies": {"good": {"dependencies": []}}}',
            '{"dependencies": {"https://user:secret@host/pkg": {}}}',
            '{"packages": {}, "lockfileVersion": 1e999}',
            '{"packages": {}, "lockfileVersion": NaN}',
        ]
        for content in cases:
            with self.subTest(content=content), self.assertRaises(ValueError) as error:
                parse_npm_lock(content)
            self.assertNotIn('secret', str(error.exception))

    def test_scans_both_npm_lockfile_names_without_exposing_urls(self):
        for filename in ('package-lock.json', 'npm-shrinkwrap.json'):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / filename).write_text(json.dumps({
                    'lockfileVersion': 3,
                    'packages': {'': {}, 'node_modules/axios': {
                        'resolved': 'https://user:secret@registry.invalid/axios'}},
                }), encoding='utf-8')
                report = scan(root)
                self.assertEqual(report['warnings'], [])
                self.assertEqual(report['totals']['Node.js'], 1)
                self.assertEqual(report['manifests'][0]['groups']['locked'], ['axios'])
                self.assertNotIn('secret', json.dumps(report))
                self.assertEqual(discover_workspaces(root)['workspaces'][0]['ecosystems'], ['Node.js'])

    def test_invalid_lockfile_returns_redacted_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'package-lock.json').write_text(
                '{"packages":{"node_modules/https://user:secret@host":{}}}',
                encoding='utf-8')
            report = scan(root)
            self.assertEqual(report['manifests'], [])
            self.assertEqual(len(report['warnings']), 1)
            self.assertNotIn('secret', json.dumps(report))


if __name__ == '__main__':
    unittest.main()
