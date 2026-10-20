"""Composer dependency-inventory and privacy regressions."""

import json
import tempfile
import unittest
from pathlib import Path

from devpilot.composer_deps import parse_composer_dependencies
from devpilot.deps import scan


class ComposerDependenciesTests(unittest.TestCase):
    def test_runtime_and_dev_packages_sorted_without_versions(self):
        result = parse_composer_dependencies(json.dumps({
            'require': {'symfony/console': '^7.2', 'php': '^8.2',
                        'vendor/secret-package': 'https://user:private-token@example.test'},
            'require-dev': {'phpunit/phpunit': '^11', 'phpstan/phpstan': '*'},
        }))
        self.assertEqual(result, {
            'require': ['php', 'symfony/console', 'vendor/secret-package'],
            'require-dev': ['phpstan/phpstan', 'phpunit/phpunit'],
        })
        self.assertNotIn('private-token', str(result))
        self.assertNotIn('https://', str(result))

    def test_empty_manifest_is_supported(self):
        self.assertEqual(parse_composer_dependencies('{}'), {})

    def test_non_object_root_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'root must be an object'):
            parse_composer_dependencies('[]')

    def test_malformed_dependency_groups_are_rejected(self):
        for group in ('require', 'require-dev'):
            with self.subTest(group=group):
                with self.assertRaisesRegex(ValueError, group):
                    parse_composer_dependencies(json.dumps({group: ['not', 'a', 'mapping']}))

    def test_malformed_json_is_rejected(self):
        with self.assertRaises(json.JSONDecodeError):
            parse_composer_dependencies('{broken')

    def test_scanner_finds_nested_composer_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / 'service'
            nested.mkdir()
            (nested / 'composer.json').write_text(json.dumps({
                'require': {'psr/log': '^3', 'php': '^8.2'},
                'require-dev': {'phpunit/phpunit': '^11'},
            }), encoding='utf-8')
            report = scan(root)
        self.assertEqual(report['totals']['PHP'], 3)
        self.assertEqual(report['manifests'], [{
            'path': 'service/composer.json',
            'ecosystem': 'PHP',
            'groups': {'require': ['php', 'psr/log'], 'require-dev': ['phpunit/phpunit']},
            'count': 3,
        }])

    def test_scanner_reports_malformed_composer_without_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'composer.json').write_text(
                '{"require": ["private-token"]}', encoding='utf-8'
            )
            report = scan(root)
        self.assertEqual(report['manifests'], [])
        self.assertEqual(len(report['warnings']), 1)
        self.assertIn('composer.json require must be an object', report['warnings'][0])
        self.assertNotIn('private-token', str(report))


if __name__ == '__main__':
    unittest.main()
