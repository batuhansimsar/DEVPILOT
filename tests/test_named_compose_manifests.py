"""Named Compose manifests are discoverable without accepting backup copies."""

import tempfile
import unittest
from pathlib import Path

from devpilot.container_manifests import is_container_manifest
from devpilot.workspaces import discover_workspaces


class NamedComposeManifestTests(unittest.TestCase):
    def test_named_compose_manifests(self):
        for filename in (
            'compose.override.yml', 'compose.dev.yaml', 'compose.ci.yml',
            'compose.v1.2.yaml', 'docker-compose.override.yml',
            'docker-compose.production.yaml',
        ):
            with self.subTest(filename=filename):
                self.assertTrue(is_container_manifest(filename))

    def test_backups_unrelated_files_and_invalid_names(self):
        for filename in (
            'compose.override.yml.bak', 'docker-compose.dev.yaml.OLD',
            'compose.dev.yml~', 'compose..yaml', 'compose.dev.json',
            'compose.yml.old', 'compose.dev.yml.tmp', 'mycompose.dev.yaml',
            'Compose.override.yaml', 'docker-compose..yml',
        ):
            with self.subTest(filename=filename):
                self.assertFalse(is_container_manifest(filename))

    def test_nested_workspace_with_only_named_compose(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = root / 'services' / 'api'
            service.mkdir(parents=True)
            (service / 'compose.dev.yaml').write_text('services: {}\n', encoding='utf-8')
            (service / 'compose.dev.yaml.bak').write_text('old\n', encoding='utf-8')
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 1)
            self.assertEqual(report['workspaces'][0]['path'], 'services/api')
            self.assertEqual(report['workspaces'][0]['ecosystems'], ['Docker'])
            self.assertEqual(report['workspaces'][0]['manifests'], [
                {'file': 'compose.dev.yaml', 'ecosystem': 'Docker'},
            ])


if __name__ == '__main__':
    unittest.main()
