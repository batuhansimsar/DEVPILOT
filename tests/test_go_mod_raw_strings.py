"""Go mod raw strings are valid require tokens for module paths and versions."""

import unittest

from devpilot.go_mod import parse_go_requirements


class GoRawRequirementTests(unittest.TestCase):
    def test_raw_paths_and_versions_in_direct_and_block_require(self):
        content = (
            'module example.org/app\n'
            'require `example.org/raw-module` v1.2.3\n'
            'require (\n'
            '  example.net/raw-version `v2.4.5` // indirect\n'
            '  `example.com/both` `v0.9.0`\n'
            '  "example.edu/quoted" `v1.0.0`\n'
            ')\n'
        )
        self.assertEqual(parse_go_requirements(content), [
            'example.com/both', 'example.edu/quoted', 'example.net/raw-version',
            'example.org/raw-module',
        ])

    def test_invalid_raw_tokens_and_other_directives_are_ignored(self):
        content = (
            'require `example.org/ok` `v1.2.3`\n'
            'require `example.org/ok` v1.2.4\n'
            'require `example.org/bad space` v1.0.0\n'
            'require `example.org/unclosed v1.0.0\n'
            'require example.org/version `v1.0.0\n'
            'require example.org/stray `v1.0.0` suffix\n'
            'replace `example.org/replaced` v1.0.0 => example.net/x v2.0.0\n'
        )
        self.assertEqual(parse_go_requirements(content), ['example.org/ok'])


if __name__ == '__main__':
    unittest.main()
