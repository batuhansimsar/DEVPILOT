"""Regression tests for malformed quotes and comments in go.mod parsing."""

import unittest

from devpilot.go_mod import parse_go_requirements


class GoModQuoteRecoveryTests(unittest.TestCase):
    def test_unterminated_double_quote_does_not_hide_later_comments(self):
        source = (
            'require "example.org/broken v1.0.0\n'
            'require example.org/valid v1.0.0 // indirect\n'
            'require example.org/next v1.1.0 /* note */\n'
        )
        with self.assertRaisesRegex(ValueError, '^go.mod contains unterminated string literal$'):
            parse_go_requirements(source)

    def test_unterminated_raw_quote_does_not_hide_later_comments(self):
        source = (
            'require `example.org/broken v1.0.0\n'
            'require example.org/valid v1.0.0 // indirect\n'
        )
        with self.assertRaisesRegex(ValueError, '^go.mod contains unterminated string literal$'):
            parse_go_requirements(source)

    def test_closed_quote_with_comment_markers_remains_literal(self):
        source = (
            'require "example.org/bad//path" v1.0.0\n'
            'require "example.org/good" v1.0.0 // indirect\n'
        )
        self.assertEqual(parse_go_requirements(source), ['example.org/good'])

    def test_malformed_quote_then_unterminated_block_comment_fails_closed(self):
        source = (
            'require "example.org/bad v1.0.0\n'
            '/* unclosed\nrequire example.org/secret v1.0.0\n'
        )
        with self.assertRaisesRegex(ValueError, '^go.mod contains unterminated string literal$'):
            parse_go_requirements(source)


if __name__ == '__main__':
    unittest.main()
