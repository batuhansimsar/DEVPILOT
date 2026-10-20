"""npm package name and dependency value safety regressions."""

import json
import tempfile
import unittest
from pathlib import Path

from devpilot.node_deps import parse_node_dependency_groups
from devpilot.deps import scan


class NodeDependencyInventoryTests(unittest.TestCase):
    def test_unscoped_and_scoped_dependencies_keep_their_declared_names(self):
        self.assertEqual(parse_node_dependency_groups({
            'dependencies': {'@types/node': '^22', 'react-dom': '^19', 'a_b.c~d': '1'},
            'devDependencies': {'vitest': '*'},
            'peerDependencies': {'react': '>=18'},
            'optionalDependencies': {'fsevents': '^2'},
        }), {
            'dependencies': ['@types/node', 'a_b.c~d', 'react-dom'],
            'devDependencies': ['vitest'],
            'peerDependencies': ['react'],
            'optionalDependencies': ['fsevents'],
        })

    def test_rejects_untrusted_names_without_leaking_names(self):
        names = ('https://user:secret@example.org/pkg', '@scope/', '/name',
                 'bad name', 'bad\x1b[31m', 'bad\nline', '__proto__', 'a' * 215)
        for name in names:
            with self.subTest(name=name), self.assertRaises(ValueError) as failure:
                parse_node_dependency_groups({'dependencies': {name: '^1'}})
            self.assertNotIn(name, str(failure.exception))
            self.assertIn('invalid package name', str(failure.exception))

    def test_rejects_non_string_specs_without_leaking_values(self):
        for spec in (None, 123, False, {'token': 'secret'}, ['^1']):
            with self.subTest(spec=spec), self.assertRaisesRegex(ValueError, 'versions must be strings'):
                parse_node_dependency_groups({'dependencies': {'react': spec}})

    def test_empty_groups_and_other_metadata(self):
        self.assertEqual(parse_node_dependency_groups({'name': 'project', 'private': True}), {})
        self.assertEqual(parse_node_dependency_groups({'dependencies': {}}), {})

    def test_scanner_redacts_rejected_manifest_names(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'package.json').write_text(json.dumps({
                'dependencies': {'https://user:secret@example.org/name': '^1'}
            }), encoding='utf-8')
            report = scan(directory)
        self.assertEqual(report['manifests'], [])
        self.assertEqual(len(report['warnings']), 1)
        self.assertIn('invalid package name', report['warnings'][0])
        self.assertNotIn('secret', json.dumps(report))

    def test_scanner_accepts_scoped_package(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'package.json').write_text(json.dumps({
                'dependencies': {'@types/node': '^22', 'react': '^19'}
            }), encoding='utf-8')
            report = scan(directory)
        self.assertEqual(report['warnings'], [])
        self.assertEqual(report['manifests'][0]['groups']['dependencies'],
                         ['@types/node', 'react'])


if __name__ == '__main__':
    unittest.main()
