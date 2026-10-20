"""End-to-end-free regression tests for single-element go.mod requirements."""

import unittest

from devpilot.go_mod import parse_go_requirements


class GoModSingleComponentTests(unittest.TestCase):
    def test_single_component_requirements_work_in_both_forms(self):
        content = (
            'module test.local/app\n'
            'require example.com v1.2.3\n'
            'require (\n'
            '  rsc.io v1.0.0 // indirect\n'
            '  localname v0.2.0\n'
            '  example.org/normal v0.3.0\n'
            ')\n'
        )
        self.assertEqual(parse_go_requirements(content), [
            'example.com', 'example.org/normal', 'localname', 'rsc.io',
        ])

    def test_single_component_paths_are_deduplicated(self):
        content = 'require example.com v1.0.0\nrequire example.com v2.0.0\n'
        self.assertEqual(parse_go_requirements(content), ['example.com'])

    def test_non_require_directives_and_invalid_versions_are_skipped(self):
        content = (
            'replace example.com v1.0.0 => other.com v1.0.0\n'
            'exclude example.com v0.9.0\n'
            'require example.com 1.0.0\n'
            'require example.com v1.0.0 extra\n'
        )
        self.assertEqual(parse_go_requirements(content), [])


if __name__ == '__main__':
    unittest.main()
