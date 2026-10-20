"""Extended Vim swap suffixes must not masquerade as active build recipes."""

import unittest

from devpilot.container_manifests import is_container_manifest


class ContainerVimSwapTests(unittest.TestCase):
    def test_rotated_vim_swap_files_are_not_build_manifests(self):
        for prefix in ('Dockerfile', 'Dockerfile.dev', 'Containerfile', 'Containerfile.prod'):
            for suffix in ('.swp', '.swo', '.swn', '.swm', '.swa', '.SWN', '.SWA',
                           '.svz', '.sua', '.sta', '.saa', '.SVZ', '.SUA', '.SAA'):
                with self.subTest(name=prefix + suffix):
                    self.assertFalse(is_container_manifest(prefix + suffix))

    def test_real_named_build_recipes_remain_supported(self):
        for name in ('Dockerfile', 'Dockerfile.dev', 'Dockerfile.prod.arm64',
                     'Containerfile', 'Containerfile.ci', 'compose.dev.yaml',
                     'docker-compose.override.yml'):
            with self.subTest(name=name):
                self.assertTrue(is_container_manifest(name))

    def test_other_filename_suffixes_are_not_mistaken_for_swaps(self):
        for name in ('Dockerfile.swq', 'Containerfile.switch', 'Dockerfile.swr',
                     'Containerfile.szq', 'Dockerfile.szz'):
            with self.subTest(name=name):
                self.assertTrue(is_container_manifest(name))


if __name__ == '__main__':
    unittest.main()
