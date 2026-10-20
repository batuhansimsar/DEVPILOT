"""Regression coverage for supported pip hash option separators."""

import unittest

from devpilot.requirements_deps import parse_requirements_dependencies


class RequirementHashSpacingTests(unittest.TestCase):
    def test_space_separated_hash_option(self):
        content = 'Requests==2.32 --hash sha256:abc123\n'
        self.assertEqual(parse_requirements_dependencies(content), ['requests'])

    def test_mixed_multiple_hash_options(self):
        content = ('My_Pkg[extra]==1.0 --hash sha256:abc123 '
                   '--hash=sha384:aabb --hash sha512:cafe # valid hashes\n')
        self.assertEqual(parse_requirements_dependencies(content), ['my-pkg'])

    def test_invalid_or_unrelated_options_do_not_create_names(self):
        content = ('bad==1 --hash sha256:NOTHEX\n'
                   'other==2 --hash sha1:abc123\n'
                   'third==3 --hash sha256:abc --trusted-host example.org\n'
                   '--hash sha256:abc123\n')
        self.assertEqual(parse_requirements_dependencies(content), [])

    def test_hashed_direct_reference_hides_credentials(self):
        content = ('Example @ https://user:private@example.org/a.whl '
                   '--hash sha256:face123\n')
        self.assertEqual(parse_requirements_dependencies(content), ['example'])

    def test_original_equals_form_and_backslash_continuation(self):
        content = ('requests==2.0 --hash=sha256:abc123 --hash=sha512:aa11\n'
                   'urllib3==2.2 \\\n'
                   '    --hash sha256:bb22\n')
        self.assertEqual(parse_requirements_dependencies(content), ['requests', 'urllib3'])


if __name__ == '__main__':
    unittest.main()
