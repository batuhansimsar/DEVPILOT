"""IDE safe-write copies must not create phantom Docker projects."""

import unittest

from devpilot.container_manifests import is_container_manifest


class JetBrainsContainerBackupTests(unittest.TestCase):
    def test_safe_write_copies_are_not_named_build_recipes(self):
        for filename in (
            'Dockerfile.___jb_tmp___', 'Dockerfile.___jb_old___',
            'Containerfile.___jb_tmp___', 'Containerfile.___jb_old___',
            'Dockerfile.release.___jb_tmp___',
            'Dockerfile.RELEASE.___JB_OLD___',
        ):
            with self.subTest(filename=filename):
                self.assertFalse(is_container_manifest(filename))

    def test_legitimate_named_manifests_are_still_detected(self):
        for filename in (
            'Dockerfile', 'Containerfile', 'Dockerfile.release',
            'Containerfile.dev', 'Dockerfile.release_arm64',
            'compose.dev.yaml', 'docker-compose.prod.yml',
        ):
            with self.subTest(filename=filename):
                self.assertTrue(is_container_manifest(filename))

    def test_non_string_inputs_do_not_crash_discovery_predicate(self):
        for filename in (None, b'Dockerfile', 0, ['Dockerfile']):
            with self.subTest(filename=filename):
                self.assertFalse(is_container_manifest(filename))


if __name__ == '__main__':
    unittest.main()
