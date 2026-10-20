"""Go module paths may contain dots but not dot-leading/trailing components."""

import unittest

from devpilot.go_mod import parse_go_requirements


class GoModulePathSegmentsTests(unittest.TestCase):
    def test_rejects_dot_segments_and_dot_edges_in_direct_requires(self):
        source = (
            'require ../secret v1.0.0\n'
            'require example.org/../secret v1.0.0\n'
            'require example.org/.hidden v1.0.0\n'
            'require example.org/dotted. v1.0.0\n'
            'require .hidden/secret v1.0.0\n'
            'require example.org/ok.module v1.0.0\n'
        )
        self.assertEqual(parse_go_requirements(source), ['example.org/ok.module'])

    def test_applies_same_rules_to_quoted_and_multiline_requires(self):
        source = (
            'require (\n'
            ' "example.org/../hidden" v1.0.0\n'
            ' "example.org/.config" v2.0.0\n'
            ' "example.org/valid.module" v3.0.0\n'
            ' example.com/v2 v2.0.1\n'
            ')\n'
        )
        self.assertEqual(parse_go_requirements(source), ['example.com/v2', 'example.org/valid.module'])


if __name__ == '__main__':
    unittest.main()
