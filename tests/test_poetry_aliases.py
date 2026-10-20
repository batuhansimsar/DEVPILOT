"""Poetry aliases must not silently conceal conflicting package specifications."""

import unittest

from devpilot.pyproject_deps import _poetry_names, parse_pyproject_dependencies


class PoetryAliasesTests(unittest.TestCase):
    def test_normalization_and_python_constraint(self):
        self.assertEqual(_poetry_names({'python': '^3.11', 'Requests': '^2', 'my_pkg': '^1'}),
                         {'requests', 'my-pkg'})

    def test_rejects_normalized_aliases(self):
        for names in ({'my_pkg': '^1', 'My-pkg': '^2'},
                      {'A.B': '^1', 'a-b': '^2'},
                      {'httpx': '^1', 'HTTPX': '^2'}):
            with self.subTest(names=names), self.assertRaisesRegex(ValueError, 'duplicate normalized'):
                _poetry_names(names)

    def test_invalid_key_does_not_echo_sensitive_name(self):
        with self.assertRaises(ValueError) as error:
            _poetry_names({'https://user:secret@example.invalid/index': '^1'})
        self.assertNotIn('secret', str(error.exception))

    def test_poetry_tables_reject_alias_conflicts(self):
        for table in ('tool.poetry.dependencies',
                      'tool.poetry.dev-dependencies',
                      'tool.poetry.group.test.dependencies'):
            source = f'[{table}]\nmy_pkg = "^1"\nMY-pkg = "^2"\n'
            with self.subTest(table=table), self.assertRaisesRegex(ValueError, 'duplicate normalized'):
                parse_pyproject_dependencies(source)

    def test_one_valid_package_is_supported(self):
        self.assertEqual(_poetry_names({'pytest': '>=8'}), {'pytest'})


if __name__ == '__main__':
    unittest.main()
