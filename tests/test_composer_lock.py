"""Composer.lock inventories never expose private source data or partial results."""

import json
import tempfile
import unittest
from pathlib import Path

from devpilot.composer_lock import parse_composer_lock


class ComposerLockTests(unittest.TestCase):
    def test_runtime_dev_inventory_is_sorted_and_privacy_safe(self):
        source = json.dumps({
            'packages': [
                {'name': 'Symfony/Console', 'version': 'v7.0.1',
                 'source': {'url': 'https://user:secret@example.test/repo'}},
                {'name': 'psr/log', 'dist': {'url': 'https://private.example.test/file'}},
            ],
            'packages-dev': [{'name': 'PHPUnit/PHPUnit', 'version': '11.0.0'}],
        })
        result = parse_composer_lock(source)
        self.assertEqual(result, {
            'locked': ['psr/log', 'symfony/console'],
            'locked-dev': ['phpunit/phpunit'],
        })
        self.assertNotIn('secret', str(result))
        self.assertNotIn('example.test', str(result))
        self.assertNotIn('11.0.0', str(result))

    def test_empty_lock_and_bom(self):
        self.assertEqual(parse_composer_lock('\ufeff{"packages": [], "packages-dev": []}'), {})
        self.assertEqual(parse_composer_lock('{}'), {})

    def test_reject_malformed_structures_without_data_leaks(self):
        invalid = [
            '[]',
            '{"packages": "secret"}',
            '{"packages": ["secret"]}',
            '{"packages": [{}]}',
            '{"packages": [{"name": "secret"}]}',
            '{"packages": [{"name": "vendor/secret"}, {"name": "Vendor/Secret"}]}',
            '{"packages-dev": [{"name": "bad name/secret"}]}',
            '{"packages": [{"name": 5}]}',
            '{"packages": [{"name": "vendor/' + 'x' * 215 + '"}]}',
            '{"packages": [{"name":"psr/log","name":"secret/token"}]}',
            '{"packages": [], "packages": []}',
            '{"packages": [], "metadata": {"x": 1, "x": 2}}',
            '{"packages": [], "secret": NaN}',
            '{"packages": [], "secret": 1e9999}',
            '{"source": "https://private.example.test", invalid}',
        ]
        for content in invalid:
            with self.subTest(case=content[:45]):
                with self.assertRaises(ValueError) as error:
                    parse_composer_lock(content)
                self.assertNotIn('secret', str(error.exception))
                self.assertNotIn('private', str(error.exception))

    def test_scan_and_workspace_discovery(self):
        from devpilot.deps import scan
        from devpilot.workspaces import discover_workspaces

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'composer.lock').write_text(json.dumps({
                'packages': [{'name': 'vendor/api', 'version': '1.0',
                              'source': {'url': 'https://user:secret@host.test'}}],
            }), encoding='utf-8')
            report = scan(root)
            workspace = discover_workspaces(root)
        self.assertEqual(report['warnings'], [])
        self.assertEqual(report['totals'], {'PHP': 1})
        self.assertEqual(report['manifests'][0]['groups'], {'locked': ['vendor/api']})
        self.assertEqual(workspace['workspaces'][0]['ecosystems'], ['PHP'])
        self.assertEqual(workspace['workspaces'][0]['manifests'], [
            {'file': 'composer.lock', 'ecosystem': 'PHP'},
        ])
        self.assertNotIn('secret', str(report))

    def test_scan_malformed_record_reports_safe_error(self):
        from devpilot.deps import scan

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'composer.lock').write_text(
                '{"packages": [{"name":"https://secret.example.test"}]}', encoding='utf-8'
            )
            report = scan(root)
        self.assertEqual(report['manifests'], [])
        self.assertEqual(len(report['warnings']), 1)
        self.assertIn('composer.lock packages has invalid package names', report['warnings'][0])
        self.assertNotIn('secret', str(report))


if __name__ == '__main__':
    unittest.main()
