"""Go modfile token separators must not be fabricated from Unicode spaces."""

import unittest

from devpilot.go_mod import parse_go_requirements


class GoModASCIIWhitespaceTests(unittest.TestCase):
    def test_unicode_whitespace_cannot_separate_directive_or_require_block(self):
        for separator in ('\u00a0', '\u2003', '\v', '\f', '\u2028'):
            with self.subTest(separator=repr(separator)):
                self.assertEqual(parse_go_requirements(
                    f'require{separator}example.org/forged v1.0.0\n'), [])
                self.assertEqual(parse_go_requirements(
                    f'require{separator}(\nexample.org/forged v1.0.0\n)\n'), [])

    def test_unicode_indentation_inside_block_cannot_create_dependency(self):
        for separator in ('\u00a0', '\u2003', '\v', '\f'):
            with self.subTest(separator=repr(separator)):
                self.assertEqual(parse_go_requirements(
                    f'require (\n{separator}example.org/forged v1.0.0\n)\n'), [])

    def test_valid_spaces_tabs_and_comments_still_work(self):
        self.assertEqual(parse_go_requirements(
            'require\t ( // indirect\n'
            '\t example.org/one\tv1.0.0\n'
            ')\n'
            'require  example.com/two \tv2.0.0\n'
        ), ['example.com/two', 'example.org/one'])


if __name__ == '__main__':
    unittest.main()
