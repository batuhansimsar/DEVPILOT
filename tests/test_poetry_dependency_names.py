"""Malformed Poetry dependency names must not silently disappear from reports."""

import unittest

from devpilot.pyproject_deps import parse_pyproject_dependencies


class PoetryDependencyNameTests(unittest.TestCase):
    def test_invalid_names_are_rejected_in_every_poetry_dependency_table(self):
        sections = (
            '[tool.poetry.dependencies]',
            '[tool.poetry.dev-dependencies]',
            '[tool.poetry.group.quality.dependencies]',
        )
        bad_names = ('bad name', 'private:secret@example.invalid', 'bad\\u001b[31m', '../unsafe')
        for section in sections:
            for name in bad_names:
                with self.subTest(section=section, name=name):
                    content = f'{section}\n"{name}" = "^1"\n'
                    with self.assertRaisesRegex(ValueError, 'invalid dependency name') as raised:
                        parse_pyproject_dependencies(content)
                    self.assertNotIn('secret', str(raised.exception))
                    self.assertNotIn(name, str(raised.exception))

    def test_valid_names_are_normalized_without_python_runtime(self):
        content = """[tool.poetry.dependencies]
python = "^3.11"
Py_Test = "^8"
[tool.poetry.dev-dependencies]
ruff = "^1"
[tool.poetry.group.docs.dependencies]
Sphinx = "^7"
"""
        self.assertEqual(parse_pyproject_dependencies(content), {
            'dependencies': ['py-test'],
            'group:dev': ['ruff'],
            'group:docs': ['sphinx'],
        })


if __name__ == '__main__':
    unittest.main()
