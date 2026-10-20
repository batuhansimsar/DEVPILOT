"""Poetry metadata-only groups must be validated before dependency inventory."""
import unittest

from devpilot.pyproject_deps import parse_pyproject_dependencies


class PoetryGroupMetadataValidationTests(unittest.TestCase):
    def test_invalid_group_name_rejected_even_without_dependencies(self):
        source = '[tool.poetry.group."secret:token@example.invalid"]\noptional = true\n'
        with self.assertRaisesRegex(ValueError, 'invalid dependency group name') as caught:
            parse_pyproject_dependencies(source)
        self.assertNotIn('secret', str(caught.exception))
        self.assertNotIn('token', str(caught.exception))

    def test_canonical_group_name_collision_is_rejected(self):
        source = '''[tool.poetry.group.Dev_Test.dependencies]
pytest = "^8"
[tool.poetry.group.dev-test.dependencies]
ruff = "^0.1"
'''
        with self.assertRaisesRegex(ValueError, 'duplicate normalized Poetry'):
            parse_pyproject_dependencies(source)

    def test_legitimate_metadata_only_group_does_not_change_inventory(self):
        source = '''[tool.poetry.group.docs]
optional = true
[tool.poetry.group.quality.dependencies]
Py_Test = "^8"
'''
        self.assertEqual(parse_pyproject_dependencies(source), {
            'group:quality': ['py-test'],
        })


if __name__ == '__main__':
    unittest.main()
