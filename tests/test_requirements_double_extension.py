"""Doubled pip suffixes are not dependency manifests."""

import unittest

from devpilot.requirements_names import is_requirements_manifest


class RequirementsDoubleExtensionTests(unittest.TestCase):
    def test_copied_or_mislabeled_documents_not_manifests(self):
        for name in (
            'requirements.txt.txt', 'requirements.in.txt',
            'requirements.dev.txt.in', 'requirements_dev.in.in',
            'local.requirements.txt.txt',
        ):
            with self.subTest(name=name):
                self.assertFalse(is_requirements_manifest(name))

    def test_valid_named_variants_still_supported(self):
        for name in (
            'requirements.txt', 'requirements-dev.txt',
            'requirements.prod.in', 'dev-requirements.txt',
            'local.requirements.in',
        ):
            with self.subTest(name=name):
                self.assertTrue(is_requirements_manifest(name))

    def test_double_extension_does_not_create_workspace(self):
        import tempfile
        from pathlib import Path

        from devpilot.core import detect_projects
        from devpilot.deps import scan
        from devpilot.workspaces import discover_workspaces

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'requirements.txt.txt').write_text('not a dependency\n', encoding='utf-8')
            self.assertNotIn('Python', detect_projects(root))
            self.assertEqual(scan(root)['manifests'], [])
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
