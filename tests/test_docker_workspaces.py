import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from devpilot.workspaces import discover_workspaces


class DockerWorkspaceTests(unittest.TestCase):
    def test_docker_only_nested_workspace(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            service = root / 'services' / 'gateway'
            service.mkdir(parents=True)
            (service / 'Dockerfile').write_text('FROM scratch\n')
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 1)
            self.assertEqual(report['workspaces'][0]['path'], 'services/gateway')
            self.assertEqual(report['workspaces'][0]['ecosystems'], ['Docker'])
            self.assertEqual(report['workspaces'][0]['manifests'], [{'file': 'Dockerfile', 'ecosystem': 'Docker'}])

    def test_compose_and_node_manifest_in_same_workspace(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'package.json').write_text('{}')
            (root / 'compose.yaml').write_text('services: {}\n')
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 1)
            self.assertEqual(report['workspaces'][0]['ecosystems'], ['Docker', 'Node.js'])
            self.assertEqual({m['file'] for m in report['workspaces'][0]['manifests']}, {'compose.yaml', 'package.json'})

    def test_named_dockerfiles_discovered(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'Dockerfile.dev').write_text('')
            (root / 'Containerfile.prod').write_text('')
            (root / 'unrelated.Dockerfile.dev').write_text('')
            report = discover_workspaces(root)
            self.assertEqual(report['workspace_count'], 1)
            self.assertEqual({m['file'] for m in report['workspaces'][0]['manifests']},
                             {'Dockerfile.dev', 'Containerfile.prod'})

    def test_other_container_manifest_names(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            for filename in ('Containerfile', 'docker-compose.yml', 'docker-compose.yaml', 'compose.yml'):
                (root / filename).write_text('')
            report = discover_workspaces(root)
            self.assertEqual(report['workspaces'][0]['ecosystems'], ['Docker'])
            self.assertEqual(len(report['workspaces'][0]['manifests']), 4)


if __name__ == '__main__':
    unittest.main()
