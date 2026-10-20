"""Direct pyproject.toml parser should match UTF-8-SIG file scanning."""

import unittest

from devpilot.pyproject_deps import parse_pyproject_dependencies


class PyprojectBOMDirectTests(unittest.TestCase):
    def test_single_bom_preserves_dependency_inventory(self):
        source = '\ufeff[project]\ndependencies = ["Requests>=2", "httpx"]\n'
        self.assertEqual(
            parse_pyproject_dependencies(source),
            {'dependencies': ['httpx', 'requests']},
        )

    def test_single_bom_supports_poetry_dependencies(self):
        source = '\ufeff[tool.poetry.dependencies]\npython = "^3.11"\nhttpx = "^0.27"\n'
        self.assertEqual(
            parse_pyproject_dependencies(source),
            {'dependencies': ['httpx']},
        )

    def test_bom_does_not_mask_invalid_toml_or_echo_values(self):
        source = '\ufeff[project]\ndependencies = ["secret@host"\n'
        with self.assertRaisesRegex(ValueError, 'Invalid pyproject.toml TOML') as raised:
            parse_pyproject_dependencies(source)
        self.assertNotIn('secret', str(raised.exception))

    def test_multiple_boms_remain_invalid(self):
        with self.assertRaisesRegex(ValueError, 'Invalid pyproject.toml TOML'):
            parse_pyproject_dependencies('\ufeff\ufeff[project]\ndependencies = []\n')


if __name__ == '__main__':
    unittest.main()
