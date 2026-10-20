"""Named Dockerfile/Containerfile recognition must reject malformed variants."""

import unittest

from devpilot.container_manifests import is_container_manifest


class NamedBuildFilenameTests(unittest.TestCase):
    def test_recognizes_valid_named_build_files(self):
        for filename in (
            'Dockerfile', 'Containerfile', 'Dockerfile.dev',
            'Dockerfile.prod.arm64', 'Containerfile.ci_1',
            'Containerfile.debug-release',
        ):
            with self.subTest(filename=filename):
                self.assertTrue(is_container_manifest(filename))

    def test_rejects_empty_or_unsafe_variant_segments(self):
        for filename in (
            'Dockerfile.', 'Dockerfile..dev', 'Dockerfile.dev.',
            'Containerfile..', 'Containerfile.prod..arm64',
            'Dockerfile.dev/test', 'Containerfile.dev\\test',
            'Dockerfile.dev name', 'Dockerfile.dev\nother',
            'Containerfile.dev@temp', 'Dockerfile.é',
        ):
            with self.subTest(filename=filename):
                self.assertFalse(is_container_manifest(filename))

    def test_backups_remain_excluded(self):
        for filename in (
            'Dockerfile.prod.bak', 'Containerfile.dev.tmp',
            'Dockerfile.dev.SWO', 'Containerfile.dockerignore',
        ):
            with self.subTest(filename=filename):
                self.assertFalse(is_container_manifest(filename))


    def test_rotated_vim_swaps_are_not_named_build_manifests(self):
        for filename in (
            'Dockerfile.dev.swp', 'Dockerfile.dev.swa',
            'Dockerfile.dev.svz', 'Containerfile.prod.sva',
            'Dockerfile.dev.suz', 'Containerfile.prod.saa',
            'Dockerfile.dev.SVZ',
        ):
            with self.subTest(filename=filename):
                self.assertFalse(is_container_manifest(filename))

    def test_non_swap_variants_remain_valid(self):
        for filename in ('Dockerfile.dev.swq', 'Containerfile.prod.swz'):
            with self.subTest(filename=filename):
                self.assertTrue(is_container_manifest(filename))


if __name__ == '__main__':
    unittest.main()
