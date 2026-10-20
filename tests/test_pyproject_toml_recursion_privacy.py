"""Malicious TOML nesting must not escape the pyproject parser or expose sources."""

import unittest

from devpilot.pyproject_deps import parse_pyproject_dependencies


class PyprojectTOMLRecursionTests(unittest.TestCase):
    def test_nested_arrays_fail_closed_without_parser_context(self):
        content = ('[tool.private]\n'
                   'url = "https://user:secret@private.invalid/simple"\n'
                   'deep = ' + '[' * 1024 + '1' + ']' * 1024 + '\n')
        with self.assertRaisesRegex(ValueError, 'Invalid pyproject.toml TOML') as raised:
            parse_pyproject_dependencies(content)
        self.assertEqual(str(raised.exception), 'Invalid pyproject.toml TOML')
        self.assertIsNone(raised.exception.__cause__)
        self.assertTrue(raised.exception.__suppress_context__)
        self.assertNotIn('secret', str(raised.exception))

    def test_valid_pep621_dependencies_still_parse(self):
        self.assertEqual(parse_pyproject_dependencies(
            '[project]\ndependencies = ["Requests>=2", "httpx==0.28"]\n'),
            {'dependencies': ['httpx', 'requests']})


if __name__ == '__main__':
    unittest.main()
