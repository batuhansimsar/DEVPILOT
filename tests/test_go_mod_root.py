"""Regressions for valid one-component Go module paths."""

import unittest

from devpilot.go_mod import parse_go_requirements


class GoRootModuleTests(unittest.TestCase):
    def test_root_domain_in_single_and_multiline_directives(self):
        content = (
            'module example.org/project\n'
            'require example.com v1.2.3\n'
            'require (\n'
            '  another.example v0.2.0 // indirect\n'
            '  example.net/submodule v2.0.0\n'
            ')\n'
            'replace unused.example v1.0.0 => example.net/new v1.0.0\n'
            'exclude excluded.example v1.0.0\n'
        )
        self.assertEqual(parse_go_requirements(content), [
            'another.example', 'example.com', 'example.net/submodule',
        ])

    def test_single_component_module_without_period(self):
        self.assertEqual(parse_go_requirements('require intranet v0.1.0\n'), ['intranet'])

    def test_malformed_required_tokens_remain_rejected(self):
        self.assertEqual(parse_go_requirements(
            'require example.com\nrequire example.net v1.0.0 extra\n'
            'require example.org/submodule v0.1.0\n'
        ), ['example.org/submodule'])


if __name__ == '__main__':
    unittest.main()
