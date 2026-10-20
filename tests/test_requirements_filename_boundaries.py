"""Keep requirement-manifest discovery from matching arbitrary lookalikes."""

import unittest

from devpilot.requirements_names import is_requirements_manifest


class RequirementsFilenameBoundariesTests(unittest.TestCase):
    def test_valid_manifest_spellings(self):
        for filename in (
            'requirements.txt', 'requirements.in', 'requirements-dev.txt',
            'requirements_dev.in', 'requirements.test.txt',
            'requirements-dev.prod.txt', 'dev-requirements.txt',
            'test-requirements.in', 'dev_test-requirements.txt',
        ):
            with self.subTest(filename=filename):
                self.assertTrue(is_requirements_manifest(filename))

    def test_lookalikes_are_not_manifests(self):
        for filename in (
            'requirementsnotes.txt', 'requirements2.txt',
            'requirements-.txt', 'requirements..txt',
            'requirements_dev..txt', '-requirements.txt',
            'dev--requirements.md', 'requirements.md',
            'myrequirements.txt', 'dev-requirements.txt.bak',
            'requirements.txt~', '', None,
        ):
            with self.subTest(filename=filename):
                self.assertFalse(is_requirements_manifest(filename))


if __name__ == '__main__':
    unittest.main()
