"""Legacy uv developer dependencies must be inventoried without leaking URLs."""

import unittest

from devpilot.pyproject_deps import parse_pyproject_dependencies


class UvLegacyDevDependenciesTests(unittest.TestCase):
    def test_uv_legacy_dev_dependencies_are_reported(self):
        content = '''
[tool.uv]
dev-dependencies = ["Py.Test>=8", "ruff[cli]==0.6", "private_pkg @ https://user:secret@example.test/pkg"]
'''
        result = parse_pyproject_dependencies(content)
        self.assertEqual(result, {'group:dev': ['private-pkg', 'py-test', 'ruff']})
        self.assertNotIn('secret', str(result))
        self.assertNotIn('example.test', str(result))

    def test_uv_legacy_and_pep735_groups_merge_and_deduplicate(self):
        content = '''
[dependency-groups]
dev = ["pytest>=7", "black"]
[tool.uv]
dev-dependencies = ["PyTest==8", "Ruff>=0.6"]
'''
        self.assertEqual(parse_pyproject_dependencies(content), {
            'group:dev': ['black', 'pytest', 'ruff']
        })

    def test_malformed_uv_configuration_rejected_without_secret_disclosure(self):
        for uv_config in (
            '"secret:password"',
            '{ dev-dependencies = "secret:password" }',
            '{ dev-dependencies = [42] }',
            '{ dev-dependencies = ["--index-url https://user:secret@example.test"] }',
        ):
            with self.subTest(uv_config=uv_config), self.assertRaises(ValueError) as caught:
                parse_pyproject_dependencies(f'[tool]\nuv = {uv_config}\n')
            self.assertNotIn('secret', str(caught.exception))
            self.assertNotIn('password', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
