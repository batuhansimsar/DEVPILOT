"""Pipfile files must appear in the dependency scanner without a lockfile."""

import json
import tempfile
import unittest
from pathlib import Path

from devpilot.deps import scan


class PipfileInventoryIntegrationTests(unittest.TestCase):
    def test_pipfile_without_lock_is_discovered_and_private_sources_hidden(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'Pipfile').write_text(
                '''[[source]]
url = "https://user:private-token@registry.example/simple"
[packages]
Flask = "==3.0"
[dev-packages]
pytest = {version = ">=8", index = "private"}
''', encoding='utf-8')
            report = scan(directory)
        self.assertEqual(report['warnings'], [])
        self.assertEqual(report['totals'], {'Python': 2})
        self.assertEqual([(item['path'], item['groups']) for item in report['manifests']],
                         [('Pipfile', {'packages': ['flask'], 'dev-packages': ['pytest']})])
        self.assertNotIn('private-token', json.dumps(report))
        self.assertNotIn('registry.example', json.dumps(report))

    def test_invalid_pipfile_produces_private_safe_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'Pipfile').write_text(
                '[packages]\n"secret@invalid" = "https://user:secret@host"\n',
                encoding='utf-8')
            report = scan(directory)
        self.assertEqual(report['manifests'], [])
        self.assertEqual(len(report['warnings']), 1)
        self.assertIn('Pipfile', report['warnings'][0])
        self.assertNotIn('secret', json.dumps(report))


if __name__ == '__main__':
    unittest.main()
