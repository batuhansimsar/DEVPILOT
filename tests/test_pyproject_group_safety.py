"""Reject untrusted pyproject group names before including them in reports."""
import unittest
from devpilot.pyproject_deps import parse_pyproject_dependencies


class PyprojectGroupSafetyTests(unittest.TestCase):
    def test_untrusted_group_names_never_reach_results_or_errors(self):
        bodies = (
            '[project.optional-dependencies]\n"bad\\u001b[31m" = ["requests"]',
            '[dependency-groups]\n"private:token@example.test" = ["requests"]',
            '[tool.poetry.group."bad group".dependencies]\nrequests = "^2"',
            '[tool.pdm.dev-dependencies]\n"secret/token" = ["requests"]',
        )
        for source in bodies:
            with self.subTest(source=source), self.assertRaises(ValueError) as caught:
                parse_pyproject_dependencies(source)
            message = str(caught.exception)
            self.assertIn('invalid dependency group name', message)
            for sensitive in ('token', 'secret', 'private', 'example.test'):
                self.assertNotIn(sensitive, message)

    def test_legitimate_group_names_and_inclusions_still_work(self):
        result = parse_pyproject_dependencies('''[project.optional-dependencies]
        "docs.api" = ["Sphinx>=7"]
        [dependency-groups]
        dev = ["pytest>=8"]
        "test-suite" = [{include-group = "dev"}, "coverage>=7"]
        ''')
        self.assertEqual(result, {
            'optional:docs.api': ['sphinx'],
            'group:dev': ['pytest'],
            'group:test-suite': ['coverage', 'pytest'],
        })


if __name__ == '__main__':
    unittest.main()
