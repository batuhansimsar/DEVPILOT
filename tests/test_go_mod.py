"""Regression tests for Go dependency declaration whitespace and scope."""

import tempfile
import unittest
from pathlib import Path

from devpilot.go_mod import parse_go_requirements
from devpilot.deps import scan


class GoModRequirementsTests(unittest.TestCase):
    def test_multiline_whitespace_and_indirect_comments(self):
        content = (
            'module example.org/demo\n'
            'require\t (\n'
            '\texample.org/alpha\tv1.0.0\n'
            '   example.net/beta   v2.0.0 // indirect\n'
            ')\n'
            'require\texample.com/gamma\tv3.4.5\n'
        )
        self.assertEqual(parse_go_requirements(content), [
            'example.com/gamma', 'example.net/beta', 'example.org/alpha',
        ])

    def test_other_directives_are_not_requirements(self):
        content = (
            'replace example.org/old v1.0.0 => example.org/new v2.0.0\n'
            'exclude example.org/banned v1.0.0\n'
            'retract v1.0.0\n'
            'require example.org/wanted v1.0.0\n'
        )
        self.assertEqual(parse_go_requirements(content), ['example.org/wanted'])

    def test_block_scope_stops_at_closing_parenthesis(self):
        content = (
            'require (\nexample.org/one v1.0.0\n)\n'
            'example.org/not-required v9.9.9\n'
            'require example.org/two v2.0.0\n'
        )
        self.assertEqual(parse_go_requirements(content), [
            'example.org/one', 'example.org/two',
        ])

    def test_deduplicates_and_ignores_malformed_lines(self):
        content = (
            'require example.org/ok v1.0.0\n'
            'require   example.org/ok   v2.0.0\n'
            'require example.org/no-version\n'
            'require example.org/bad v1.0.0 extra\n'
            'require (\nexample.org/inside v1.0.0 // indirect\n)\n'
        )
        self.assertEqual(parse_go_requirements(content), [
            'example.org/inside', 'example.org/ok',
        ])

    def test_dependency_inventory_uses_strict_go_parser(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'go.mod').write_text(
                'module example.org/project\n'
                'require example.org/ok v1.0.0\n'
                'require example.org/bad v1.0.0 extra\n',
                encoding='utf-8',
            )
            groups = scan(root)['manifests'][0]['groups']
            self.assertEqual(groups['require'], ['example.org/ok'])


if __name__ == '__main__':
    unittest.main()
