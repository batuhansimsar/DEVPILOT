"""Backslash-newline joining must preserve adjacency in pip requirements."""

import unittest

from devpilot.requirements_deps import parse_requirements_dependencies


class RequirementsContinuationAdjacencyTests(unittest.TestCase):
    def test_continued_package_name(self):
        self.assertEqual(
            parse_requirements_dependencies('some\\\n_package==1.0\n'),
            ['some-package'],
        )

    def test_continued_version(self):
        self.assertEqual(
            parse_requirements_dependencies('requests==2.\\\n31\n'),
            ['requests'],
        )

    def test_continued_direct_reference_omits_private_url(self):
        source = 'Private_Pkg @ https://user:secret@example.invalid/pkg\\\n.whl\n'
        names = parse_requirements_dependencies(source)
        self.assertEqual(names, ['private-pkg'])
        self.assertNotIn('secret', repr(names))

    def test_spaced_hash_continuation_is_still_supported(self):
        self.assertEqual(
            parse_requirements_dependencies('urllib3==2.2 \\\n  --hash=sha256:aabb\n'),
            ['urllib3'],
        )

    def test_backslash_followed_by_spaces_is_not_continuation(self):
        source = '--index-url https://example.invalid/simple\\  \nvalid==2\n'
        self.assertEqual(parse_requirements_dependencies(source), ['valid'])


if __name__ == '__main__':
    unittest.main()
