"""Cargo.lock inventory, malformed input and privacy regressions."""

import tempfile
import unittest
from pathlib import Path

from devpilot.cargo_lock import parse_cargo_lock


class CargoLockTests(unittest.TestCase):
    def test_standard_v3_v4_lockfiles_and_duplicate_names(self):
        lock = '''version = 4
[[package]]
name = "demo_app"
version = "0.1.0"
[[package]]
name = "serde-json"
version = "1.0.0"
source = "registry+https://user:secret@example.invalid/index"
checksum = "private-checksum"
[[package]]
name = "serde-json"
version = "2.0.0"
'''
        result = parse_cargo_lock(lock)
        self.assertEqual(result, ['demo_app', 'serde-json'])
        self.assertNotIn('secret', repr(result))
        self.assertNotIn('private', repr(result))
        self.assertNotIn('example.invalid', repr(result))

    def test_empty_and_bom(self):
        self.assertEqual(parse_cargo_lock('\ufeffversion = 3\n'), [])
        self.assertEqual(parse_cargo_lock('package = []\n'), [])

    def test_fails_closed_on_invalid_package_records(self):
        invalid = [
            'package = "wrong"\n',
            'package = ["not a table"]\n',
            '[[package]]\nversion = "1.2"\n',
            '[[package]]\nname = "bad crate"\n',
            '[[package]]\nname = "https://user:secret@example.invalid"\n',
            '[[package]]\nname = 123\n',
            '[[package]]\nname = "' + 'a' * 215 + '"\n',
        ]
        for source in invalid:
            with self.subTest(source=source[:30]):
                with self.assertRaises(ValueError) as err:
                    parse_cargo_lock(source)
                self.assertNotIn('secret', str(err.exception))
                self.assertNotIn('https', str(err.exception))

    def test_malformed_toml_error_keeps_source_private(self):
        with self.assertRaisesRegex(ValueError, 'invalid Cargo.lock TOML') as err:
            parse_cargo_lock('source = "https://user:secret@example.invalid"\ninvalid = [\n')
        self.assertNotIn('secret', str(err.exception))

    def test_dependency_scanner_integration(self):
        from devpilot.deps import scan

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Cargo.lock').write_text(
                'version = 3\n[[package]]\nname = "serde"\nversion = "1.0.0"\n'
                'source = "registry+https://user:secret@example.invalid/index"\n',
                encoding='utf-8',
            )
            report = scan(root)
        self.assertEqual(report['warnings'], [])
        self.assertEqual(report['totals'], {'Rust': 1})
        self.assertEqual(report['manifests'][0]['groups'], {'locked': ['serde']})
        self.assertNotIn('secret', repr(report))

    def test_workspace_discovery_with_cargo_lock_only(self):
        from devpilot.workspaces import discover_workspaces

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Cargo.lock').write_text('version = 4\n', encoding='utf-8')
            report = discover_workspaces(root)
        self.assertEqual(report['workspace_count'], 1)
        self.assertEqual(report['workspaces'][0]['ecosystems'], ['Rust'])
        self.assertEqual(report['workspaces'][0]['manifests'], [
            {'file': 'Cargo.lock', 'ecosystem': 'Rust'}
        ])


if __name__ == '__main__':
    unittest.main()
