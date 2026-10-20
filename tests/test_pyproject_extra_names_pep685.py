"""PEP 685 optional extra names must be canonical and non-ambiguous."""

import unittest

from devpilot.pyproject_deps import parse_pyproject_dependencies


class PyprojectExtraNamesTests(unittest.TestCase):
    def test_canonicalizes_case_and_separators(self):
        content = '''
[project.optional-dependencies]
"QA_checks" = ["PyTest>=8"]
'''
        self.assertEqual(
            parse_pyproject_dependencies(content),
            {'optional:qa-checks': ['pytest']},
        )

    def test_ambiguous_normalized_extras_rejected(self):
        content = '''
[project.optional-dependencies]
"QA_checks" = ["pytest"]
"qa.checks" = ["coverage"]
'''
        with self.assertRaisesRegex(ValueError, 'duplicate normalized optional'):
            parse_pyproject_dependencies(content)

    def test_invalid_extra_does_not_expose_private_key(self):
        content = '''
[project.optional-dependencies]
"https://user:private-token@example.invalid" = ["pytest"]
'''
        with self.assertRaises(ValueError) as error:
            parse_pyproject_dependencies(content)
        self.assertNotIn('private-token', str(error.exception))


if __name__ == '__main__':
    unittest.main()
