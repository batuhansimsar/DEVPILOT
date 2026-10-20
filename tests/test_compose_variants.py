"""Regression coverage for named Compose manifests and backup exclusions."""

import unittest

from devpilot.container_manifests import is_container_manifest


class ComposeVariantTests(unittest.TestCase):
    def test_named_compose_layers_are_recognized(self):
        for name in (
            'compose.dev.yaml', 'compose.test.yml', 'compose.local.prod.yaml',
            'docker-compose.override.yml', 'docker-compose.prod-us.yaml',
            'docker-compose.ci_test.yml',
        ):
            with self.subTest(name=name):
                self.assertTrue(is_container_manifest(name))

    def test_backup_and_temp_layers_are_not_manifests(self):
        for name in (
            'compose.dev.yaml.bak', 'compose.test.yml.old',
            'docker-compose.override.yml.tmp', 'compose.dev.yaml~',
            'docker-compose.prod.yml.SWP', 'compose.prod.yaml.dockerignore',
        ):
            with self.subTest(name=name):
                self.assertFalse(is_container_manifest(name))

    def test_similarly_named_files_remain_unrecognized(self):
        for name in (
            'my-compose.dev.yaml', 'compose..yaml', 'compose.dev..yaml',
            'compose.dev.json', 'compose.dev.yaml.txt',
            'Compose.dev.yaml', 'docker-compose.yml.example',
        ):
            with self.subTest(name=name):
                self.assertFalse(is_container_manifest(name))

    def test_existing_manifest_names_still_work(self):
        for name in ('Dockerfile', 'Containerfile', 'Dockerfile.dev',
                     'Containerfile.prod', 'compose.yml', 'compose.yaml',
                     'docker-compose.yml', 'docker-compose.yaml'):
            with self.subTest(name=name):
                self.assertTrue(is_container_manifest(name))


if __name__ == '__main__':
    unittest.main()
