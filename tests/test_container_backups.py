"""Do not mistake edited/backup image build recipes for active Docker manifests."""

import unittest

from devpilot.container_manifests import is_container_manifest


class ContainerBackupDetectionTests(unittest.TestCase):
    def test_named_dockerfile_backup_extensions_are_ignored(self):
        for base in ('Dockerfile', 'Dockerfile.dev', 'Containerfile', 'Containerfile.prod'):
            for suffix in ('.old', '.orig', '.save', '.swo', '.OLD', '.ORIG', '.SAVE', '.SWO'):
                with self.subTest(filename=base + suffix):
                    self.assertFalse(is_container_manifest(base + suffix))

    def test_live_named_build_recipes_remain_detectable(self):
        for filename in ('Dockerfile', 'Dockerfile.dev', 'Dockerfile.production',
                         'Containerfile', 'Containerfile.prod', 'Containerfile.ci'):
            with self.subTest(filename=filename):
                self.assertTrue(is_container_manifest(filename))

    def test_compose_files_and_other_backup_types_unchanged(self):
        for filename in ('compose.yml', 'compose.yaml', 'docker-compose.yml', 'docker-compose.yaml'):
            with self.subTest(filename=filename):
                self.assertTrue(is_container_manifest(filename))
        for filename in ('Dockerfile.bak', 'Dockerfile.dev.backup', 'Containerfile.dev.tmp',
                         'Containerfile.ci.swp', 'Dockerfile.dockerignore'):
            with self.subTest(filename=filename):
                self.assertFalse(is_container_manifest(filename))


if __name__ == '__main__':
    unittest.main()
