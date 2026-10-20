"""PEP 735 dependency-group inventory regression tests."""
import unittest
from devpilot.pyproject_deps import parse_pyproject_dependencies


class DependencyGroupsTests(unittest.TestCase):
    def test_group_only_project(self):
        data = '[dependency-groups]\ndev = ["pytest>=8", "Ruff==0.6"]\n'
        self.assertEqual(parse_pyproject_dependencies(data),
                         {'group:dev': ['pytest', 'ruff']})

    def test_recursive_includes_deduplicate_and_redact(self):
        data = """
[project]
dependencies = ["Requests>=2"]
[dependency-groups]
quality = ["Ruff>=0.5", "pytest==8"]
test = ["pytest>=7", {include-group = "QUALITY"}]
all = [{include-group = "test"}, "my_pkg @ https://user:secret@example.invalid/file"]
"""
        actual = parse_pyproject_dependencies(data)
        self.assertEqual(actual, {
            'dependencies': ['requests'],
            'group:all': ['my-pkg', 'pytest', 'ruff'],
            'group:quality': ['pytest', 'ruff'],
            'group:test': ['pytest', 'ruff'],
        })
        self.assertNotIn('secret', str(actual))

    def test_ambiguous_normalized_groups_are_rejected(self):
        data = '[dependency-groups]\nDev_Test = ["pytest"]\ndev-test = ["ruff"]\n'
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            parse_pyproject_dependencies(data)

    def test_circular_include_is_rejected(self):
        data = ('[dependency-groups]\na = [{include-group = "b"}]\n'
                'b = [{include-group = "a"}]\n')
        with self.assertRaisesRegex(ValueError, 'cyclic'):
            parse_pyproject_dependencies(data)

    def test_missing_include_is_rejected_without_disclosing_name(self):
        data = '[dependency-groups]\na = [{include-group = "private-secret-name"}]\n'
        with self.assertRaisesRegex(ValueError, 'unknown') as context:
            parse_pyproject_dependencies(data)
        self.assertNotIn('private-secret-name', str(context.exception))

    def test_bad_group_entries_rejected(self):
        for entry in ('42', '{include-group = 42}', '{unknown = "secret"}',
                      '{include-group = "test", extra = "secret"}'):
            with self.subTest(entry=entry):
                with self.assertRaises(ValueError):
                    parse_pyproject_dependencies(f'[dependency-groups]\ntest = [{entry}]\n')

    def test_pep621_compatibility(self):
        self.assertEqual(parse_pyproject_dependencies(
            '[project]\ndependencies = ["Requests>=2", "my_pkg @ https://user:token@example.org/w"]\n'
            '[project.optional-dependencies]\ndev = ["pytest>=8"]\n'
        ), {'dependencies': ['my-pkg', 'requests'], 'optional:dev': ['pytest']})


if __name__ == '__main__':
    unittest.main()
