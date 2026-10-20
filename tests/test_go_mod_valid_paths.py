"""Go module paths containing valid punctuation must survive inventory parsing."""

import unittest

from devpilot.go_mod import parse_go_requirements


class GoModValidPathsTests(unittest.TestCase):
    def test_plus_and_tilde_in_require_directives(self):
        source = (
            'module example.org/demo\n'
            'require example.org/foo+bar v1.2.3\n'
            'require (\n'
            '  example.net/lib~next v0.9.0 // indirect\n'
            '  github.com/example/name.with_more-punctuation v2.0.0\n'
            ')\n'
        )
        self.assertEqual(parse_go_requirements(source), [
            'example.net/lib~next',
            'example.org/foo+bar',
            'github.com/example/name.with_more-punctuation',
        ])

    def test_rejects_unsupported_punctuation_and_directives(self):
        source = (
            'require example.org/with!bang v1.2.3\n'
            'require example.org/with:colon v1.2.3\n'
            'replace example.org/replaced+name v1.2.3 => example.net/x v2.0.0\n'
            'require example.org/valid~suffix v3.0.0\n'
        )
        self.assertEqual(parse_go_requirements(source), ['example.org/valid~suffix'])

    def test_plain_require_and_tabs_unchanged(self):
        self.assertEqual(parse_go_requirements('require\t(\nfoo.example/bar v1.0.0\n)\n'), ['foo.example/bar'])


if __name__ == '__main__':
    unittest.main()
