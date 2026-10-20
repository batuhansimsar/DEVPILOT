"""Quoted and escaped Go module paths must appear in dependency inventories."""

import unittest

from devpilot.go_mod import parse_go_requirements


class QuotedGoRequirementTests(unittest.TestCase):
    def test_quoted_single_line_and_block_requirements(self):
        content = (
            'module example.org/test\n'
            'require "example.org/quoted" v1.2.3\n'
            'require (\n'
            '\t"example.net/sub+module" "v0.4.0" // indirect\n'
            '\texample.com/unquoted v2.0.0\n'
            ')\n'
        )
        self.assertEqual(parse_go_requirements(content), [
            'example.com/unquoted', 'example.net/sub+module', 'example.org/quoted',
        ])

    def test_decodes_go_string_escapes_in_module_paths(self):
        source = (
            'require "example.org/quote\\x64" v1.0.0\n'
            'require "example.net/\\u0061pi" "v1.2.3"\n'
            'require "example.com/\\141bc" v2.0.0\n'
        )
        self.assertEqual(parse_go_requirements(source), [
            'example.com/abc', 'example.net/api', 'example.org/quoted',
        ])

    def test_quoted_paths_do_not_contribute_to_other_directives(self):
        content = (
            'replace "example.org/replaced" v1.0.0 => example.net/new v1.0.0\n'
            'exclude "example.org/excluded" v1.0.0\n'
            'require "example.org/wanted" v1.0.0\n'
        )
        self.assertEqual(parse_go_requirements(content), ['example.org/wanted'])

    def test_rejects_malformed_escapes_and_preserves_deduplication(self):
        content = (
            'require "example.org/ok" v1.0.0\n'
            'require example.org/ok v1.1.0\n'
            'require "example.org/bad\\q" v1.0.0\n'
            'require "example.org/bad space" v1.0.0\n'
            'require "example.org/extra" v1.0.0 trailing\n'
        )
        self.assertEqual(parse_go_requirements(content), ['example.org/ok'])


if __name__ == '__main__':
    unittest.main()
