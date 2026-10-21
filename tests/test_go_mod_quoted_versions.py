"""Go's go.mod grammar supports quoted versions as well as quoted paths."""

import unittest

from devpilot.go_mod import parse_go_requirements


class GoQuotedVersionTests(unittest.TestCase):
    def test_double_quoted_versions_are_inventoried(self):
        content = (
            'module example.org/local\n'
            'require example.org/alpha "v1.2.3"\n'
            'require (\n'
            ' "example.org/beta" "v2.3.4" // indirect\n'
            ' example.org/gamma v3.0.0\n'
            ')\n'
        )
        self.assertEqual(parse_go_requirements(content), [
            'example.org/alpha', 'example.org/beta', 'example.org/gamma',
        ])

    def test_unbalanced_or_malformed_versions_are_ignored(self):
        content = (
            'require example.org/no-close "v1.0.0\n'
            'require example.org/no-open v1.0.0"\n'
            'require example.org/bad v1.0.0"garbage\n'
            'require example.org/good "v2.0.0"\n'
        )
        with self.assertRaisesRegex(ValueError, '^go.mod contains unterminated string literal


if __name__ == '__main__':
    unittest.main()
):
            parse_go_requirements(content)
        self.assertEqual(parse_go_requirements(
            'require example.org/good "v2.0.0"\n'
        ), ['example.org/good'])


if __name__ == '__main__':
    unittest.main()
