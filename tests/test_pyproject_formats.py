"""Regression checks for PEP 735, Poetry and PDM dependency inventory."""

import unittest

from devpilot.pyproject_deps import parse_pyproject_dependencies


class PyprojectFormatTests(unittest.TestCase):
    def test_pep621_and_optional_dependencies_redact_direct_urls(self):
        content = '''
[project]
dependencies = ["Requests>=2", "My_Pkg[foo] @ https://user:secret@example.test/pkg", "Flask ; python_version >= '3.10'"]
[project.optional-dependencies]
test = ["Py.Test>=8", "requests==2"]
'''
        result = parse_pyproject_dependencies(content)
        self.assertEqual(result, {'dependencies': ['flask', 'my-pkg', 'requests'],
                                  'optional:test': ['py-test', 'requests']})
        self.assertNotIn('secret', str(result))
        self.assertNotIn('example.test', str(result))

    def test_pep735_dependency_groups_and_include_directive(self):
        content = '''
[dependency-groups]
test = ["pytest>=8", { include-group = "lint" }]
lint = ["Ruff==0.8"]
'''
        self.assertEqual(parse_pyproject_dependencies(content), {
            'group:lint': ['ruff'], 'group:test': ['pytest', 'ruff'],
        })

    def test_dependency_group_cycle_and_missing_reference_fail_without_leaking_names(self):
        for content in (
            '[dependency-groups]\na = [{include-group="a"}]',
            '[dependency-groups]\na = [{include-group="b"}]',
        ):
            with self.subTest(content=content):
                with self.assertRaises(ValueError) as raised:
                    parse_pyproject_dependencies(content)
                self.assertNotIn('include-group="', str(raised.exception))

    def test_empty_groups_are_retained_for_compatibility(self):
        self.assertEqual(parse_pyproject_dependencies(
            '[project]\ndependencies=[]\n[project.optional-dependencies]\ntest=[]\n'
        ), {'dependencies': [], 'optional:test': []})

    def test_poetry_and_pdm_dev_dependencies(self):
        content = '''
[tool.poetry.dependencies]
python = "^3.10"
Requests = {git = "https://user:token@example.test/repo"}
[tool.poetry.group.dev.dependencies]
pytest = "^8"
[tool.poetry.dev-dependencies]
Black = "^24"
[tool.pdm.dev-dependencies]
test = ["Hypothesis>=6"]
'''
        result = parse_pyproject_dependencies(content)
        self.assertEqual(result, {
            'dependencies': ['requests'], 'group:dev': ['black', 'pytest'],
            'group:test': ['hypothesis'],
        })
        self.assertNotIn('token', str(result))

    def test_unrelated_tool_config_not_reported(self):
        self.assertEqual(parse_pyproject_dependencies('''
[tool.pytest.ini_options]
addopts = "--maxfail=1"
'''), {})

    def test_invalid_toml_raises_without_leaking_contents(self):
        with self.assertRaisesRegex(ValueError, '^Invalid pyproject.toml TOML$'):
            parse_pyproject_dependencies('[project]\ndependencies = ["super-secret"')

    def test_invalid_requirement_rejected_without_leaking_value(self):
        for content in (
            '[project]\ndependencies = ["git+https://user:secret@example.test/repo"]',
            '[project]\ndependencies = "password=secret"',
        ):
            with self.subTest(content=content):
                with self.assertRaises(ValueError) as raised:
                    parse_pyproject_dependencies(content)
                self.assertNotIn('secret', str(raised.exception))


if __name__ == '__main__':
    unittest.main()
