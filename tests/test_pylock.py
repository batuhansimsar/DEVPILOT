"""PEP 751 lockfile inventory, discovery, and credential privacy."""

import tempfile
import unittest
from pathlib import Path

from devpilot.core import analyze_project, detect_projects
from devpilot.deps import scan
from devpilot.pylock import is_pylock_manifest, parse_pylock
from devpilot.workspaces import discover_workspaces


class PylockTests(unittest.TestCase):
    def test_standard_and_named_filenames(self):
        for name in ('pylock.toml', 'pylock.dev.toml', 'pylock.production_2.toml'):
            self.assertTrue(is_pylock_manifest(name))
        for name in ('Pylock.toml', 'pylock..toml', 'pylock.dev.extra.toml',
                     'pylock.toml.bak', 'other.toml'):
            self.assertFalse(is_pylock_manifest(name))

    def test_parses_names_without_sources_or_versions(self):
        content = '''\ufefflock-version = "1.0"
created-by = "tester"
[[packages]]
name = "My_Pkg"
version = "1.2"
[packages.archive]
url = "https://user:secret@example.invalid/a.whl"
[[packages]]
name = "my.pkg"
[[packages]]
name = "Requests"
'''
        result = parse_pylock(content)
        self.assertEqual(result, ['my-pkg', 'requests'])
        self.assertNotIn('secret', repr(result))

    def test_empty_package_array(self):
        self.assertEqual(parse_pylock('lock-version = "1.0"\ncreated-by = "tool"\npackages = []\n'), [])

    def test_rejects_invalid_structure_and_names_without_leaks(self):
        header = 'lock-version = "1.0"\ncreated-by = "tool"\n'
        invalid = [
            'created-by = "tool"\npackages = []',
            'lock-version = "2.0"\ncreated-by = "tool"\npackages = []',
            'lock-version = "1.0"\npackages = []',
            header,
            header + 'packages = "wrong"',
            header + 'packages = ["wrong"]',
            header + '[[packages]]\nversion = "1"',
            header + '[[packages]]\nname = "https://user:secret@example.invalid"',
            header + '[[packages]]\nname = "bad name"',
            header + '[[packages]]\nname = "' + 'a' * 215 + '"',
        ]
        for value in invalid:
            with self.subTest(value=value[:40]), self.assertRaises(ValueError) as error:
                parse_pylock(value)
            self.assertNotIn('secret', str(error.exception))
            self.assertNotIn('https', str(error.exception))

    def test_invalid_and_nested_toml_error_is_private(self):
        for content in ('created-by = "https://user:secret@host"\nvalue = [',
                        'lock-version = "1.0"\ncreated-by = "tool"\nnested = ' +
                        '[' * 1500 + '"secret"' + ']' * 1500):
            with self.assertRaisesRegex(ValueError, 'invalid pylock.toml TOML') as error:
                parse_pylock(content)
            self.assertIsNone(error.exception.__cause__)
            self.assertNotIn('secret', str(error.exception))

    def test_named_lockfile_is_found_by_analyze_workspaces_and_deps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'pylock.dev.toml').write_text(
                'lock-version = "1.0"\ncreated-by = "tool"\n'
                '[[packages]]\nname = "httpx"\n'
                '[[packages]]\nname = "Pydantic_Core"\n', encoding='utf-8')
            (root / 'pylock.dev.extra.toml').write_text('not a manifest')
            self.assertIn('Python', detect_projects(root))
            analysis = analyze_project(root)
            self.assertIn('pylock.dev.toml', analysis['key_files'])
            self.assertNotIn('pylock.dev.extra.toml', analysis['key_files'])
            spaces = discover_workspaces(root)
            self.assertEqual(spaces['workspace_count'], 1)
            self.assertEqual(spaces['workspaces'][0]['manifests'],
                             [{'file': 'pylock.dev.toml', 'ecosystem': 'Python'}])
            result = scan(root)
            self.assertEqual(result['warnings'], [])
            self.assertEqual(result['totals'], {'Python': 2})
            self.assertEqual(result['manifests'][0]['groups'],
                             {'locked': ['httpx', 'pydantic-core']})

    def test_invalid_packages_warn_without_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'pylock.toml').write_text(
                'lock-version = "1.0"\ncreated-by = "tool"\n'
                '[[packages]]\nname = "https://user:secret@example.invalid"\n')
            report = scan(root)
        self.assertEqual(report['manifests'], [])
        self.assertEqual(len(report['warnings']), 1)
        self.assertNotIn('secret', repr(report))

    def test_symlinks_are_not_inspected(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            target = Path(external) / 'pylock.toml'
            target.write_text('lock-version = "1.0"\ncreated-by = "tool"\npackages = []\n')
            try:
                (root / 'pylock.toml').symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertEqual(scan(root)['manifests'], [])
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)
            self.assertNotIn('Python', detect_projects(root))


if __name__ == '__main__':
    unittest.main()
