"""Regressions for Go's double-quoted module requirement syntax."""

import unittest

from devpilot.go_mod import parse_go_requirements


class QuotedGoModulesTests(unittest.TestCase):
    def test_quoted_paths_in_direct_and_block_requires(self):
        self.assertEqual(parse_go_requirements(
            'module example.org/app\n'
            'require "example.com" v1.0.0\n'
            'require (\n'
            '  "example.net/module" v2.0.0 // indirect\n'
            '  example.org/plain v0.3.0\n'
            ')\n'
        ), ['example.com', 'example.net/module', 'example.org/plain'])

    def test_rejects_missing_or_unbalanced_quotes(self):
        with self.assertRaisesRegex(ValueError, '^go.mod contains unterminated string literal


if __name__ == '__main__':
    unittest.main()
):
            parse_go_requirements(
                'require "example.com/missing v1.0.0\n'
                'require example.com/trailing" v1.0.0\n'
                'require "" v1.0.0\n'
                'require "example.org/good" v1.2.3\n'
            )
        self.assertEqual(parse_go_requirements(
            'require "" v1.0.0\nrequire "example.org/good" v1.2.3\n'
        ), ['example.org/good'])


if __name__ == '__main__':
    unittest.main()
