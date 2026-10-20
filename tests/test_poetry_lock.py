"""Poetry lockfile inventory and privacy regression tests."""

import json
import tempfile
import unittest
from pathlib import Path

from devpilot.poetry_lock import parse_poetry_lock


class PoetryLockTests(unittest.TestCase):
    def test_normalizes_and_deduplicates_without_exposing_sources(self):
        lock = '''# Poetry 1.x/2.x-style package tables
[[package]]
name = "My_Pkg"
version = "1.2.3"
category = "main"
optional = false
python-versions = ">=3.10"
[package.source]
type = "legacy"
url = "https://user:secret@example.invalid/simple"
reference = "private"

[[package]]
name = "my-pkg"
version = "1.3"
groups = ["dev"]

[[package]]
name = "Requests"
version = "2.32.0"

[metadata]
lock-version = "2.1"
'''
        result = parse_poetry_lock(lock)
        self.assertEqual(result, ["my-pkg", "requests"])
        self.assertNotIn("secret", str(result))
        self.assertNotIn("example.invalid", str(result))

    def test_missing_or_empty_packages(self):
        self.assertEqual(parse_poetry_lock('[metadata]\nlock-version = "2.1"\n'), [])
        self.assertEqual(parse_poetry_lock('package = []\n'), [])

    def test_rejects_invalid_records_without_reflecting_secrets(self):
        invalid = (
            'package = "invalid"\n',
            'package = ["not-a-table"]\n',
            '[[package]]\nversion = "1.0"\n',
            '[[package]]\nname = "https://user:secret@example.invalid"\n',
            '[[package]]\nname = "bad name"\n',
            '[[package]]\nname = "bad\\u0000name"\n',
            '[[package]]\nname = 123\n',
            '[[package]]\nname = "' + 'x' * 215 + '"\n',
        )
        for source in invalid:
            with self.subTest(source=source[:30]):
                with self.assertRaises(ValueError) as raised:
                    parse_poetry_lock(source)
                self.assertNotIn('secret', str(raised.exception))
                self.assertNotIn('https', str(raised.exception))

    def test_malformed_toml_uses_private_error(self):
        with self.assertRaisesRegex(ValueError, 'invalid poetry.lock TOML') as raised:
            parse_poetry_lock('source = "https://user:secret@example.invalid"\nbroken = [\n')
        self.assertNotIn('secret', str(raised.exception))

    def test_scan_integration(self):
        from devpilot.deps import scan

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / 'service'
            project.mkdir()
            (project / 'poetry.lock').write_text('''[[package]]
name = "Pydantic_Core"
version = "2.0"
[[package]]
name = "httpx"
version = "0.28"
''', encoding='utf-8')
            report = scan(root)
        self.assertEqual(report['warnings'], [])
        self.assertEqual(report['totals'], {'Python': 2})
        self.assertEqual(report['manifests'][0]['path'], 'service/poetry.lock')
        self.assertEqual(report['manifests'][0]['groups'], {'locked': ['httpx', 'pydantic-core']})
        self.assertNotIn('version', json.dumps(report))

    def test_workspaces_discovers_poetry_only_project(self):
        from devpilot.workspaces import discover_workspaces

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'poetry.lock').write_text('[[package]]\nname = "httpx"\n', encoding='utf-8')
            result = discover_workspaces(root)
        self.assertEqual(result['workspace_count'], 1)
        self.assertEqual(result['workspaces'][0]['ecosystems'], ['Python'])
        self.assertEqual(result['workspaces'][0]['manifests'], [
            {'file': 'poetry.lock', 'ecosystem': 'Python'}
        ])


if __name__ == '__main__':
    unittest.main()
