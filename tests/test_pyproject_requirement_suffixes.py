"""Reject incomplete or non-PEP-508 suffixes without logging secrets."""
import unittest

from devpilot.pyproject_deps import parse_pyproject_dependencies


class RequirementSuffixTests(unittest.TestCase):
    def test_invalid_suffixes_are_not_silently_accepted(self):
        for requirement in ('Flask unexpected', 'Requests @', 'requests ;', 'pytest ['):
            with self.subTest(requirement=requirement):
                with self.assertRaisesRegex(ValueError, 'invalid requirement'):
                    parse_pyproject_dependencies('[project]\ndependencies = [' + repr(requirement).replace("'", '"') + ']')

    def test_valid_requirement_names_only(self):
        content = '''[project]
dependencies = ["HTTPX>=0.27", "private_pkg @ https://user:secret@example.invalid/archive", "Requests[security]>=2"]
[dependency-groups]
dev = ["pytest>=8"]
'''
        result = parse_pyproject_dependencies(content)
        self.assertEqual(result['dependencies'], ['httpx', 'private-pkg', 'requests'])
        self.assertEqual(result['group:dev'], ['pytest'])
        self.assertNotIn('secret', str(result))


if __name__ == '__main__':
    unittest.main()
