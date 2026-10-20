"""Go dependency inventory must accept legal module path shapes."""

import unittest

from devpilot.go_mod import parse_go_requirements


class GoModulePathTests(unittest.TestCase):
    def test_single_component_domain_path(self):
        self.assertEqual(parse_go_requirements(
            'module example.org/app\nrequire example.com v1.2.3\n'
        ), ['example.com'])

    def test_tilde_in_module_path(self):
        self.assertEqual(parse_go_requirements(
            'require (\nexample.org/lib~next v1.2.3\n'
            'example.com/child~2/helper v0.0.1 // indirect\n)\n'
        ), ['example.com/child~2/helper', 'example.org/lib~next'])

    def test_plus_path_compatibility(self):
        self.assertEqual(parse_go_requirements(
            'require example.com/x+y v1.0.0\n'
        ), ['example.com/x+y'])

    def test_invalid_entries_still_ignored(self):
        self.assertEqual(parse_go_requirements(
            'require example.com v1.0.0 unexpected\n'
            'require https://example.org/pkg v1.0.0\n'
            'require example.com/valid v2.0.0\n'
            'replace example.com/other v3.0.0\n'
        ), ['example.com/valid'])

    def test_existing_multiline_format_unchanged(self):
        self.assertEqual(parse_go_requirements(
            'require (\nexample.org/first v1.0.0\n)\n'
            'require\texample.net/second\tv1.2.3\n'
        ), ['example.net/second', 'example.org/first'])


if __name__ == '__main__':
    unittest.main()
