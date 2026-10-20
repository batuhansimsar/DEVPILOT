"""Malformed Go string literals must not hide dependency declarations."""

import unittest

from devpilot.go_mod import parse_go_requirements


class GoModUnterminatedStringTests(unittest.TestCase):
    def test_unterminated_double_quote_before_newline_fails_closed(self):
        source = ('require example.org/first v1.2.3\n'
                  'require "private.example/secret\n'
                  'require example.org/second v4.5.6\n')
        with self.assertRaisesRegex(ValueError, r'^go.mod contains unterminated string literal$') as caught:
            parse_go_requirements(source)
        self.assertNotIn('private.example', str(caught.exception))

    def test_unterminated_raw_string_at_eof_fails_closed(self):
        with self.assertRaisesRegex(ValueError, r'^go.mod contains unterminated string literal$'):
            parse_go_requirements('require `example.org/missing v1.0.0')

    def test_closed_strings_and_comment_quotes_are_valid(self):
        source = ('// "unfinished quote in a comment\n'
                  '/* `another unfinished quote in comment */\n'
                  'require "example.org/quoted" v1.0.0\n'
                  'require `example.org/raw` v2.0.0\n')
        self.assertEqual(parse_go_requirements(source), ['example.org/quoted', 'example.org/raw'])

    def test_escaped_quote_does_not_close_string(self):
        with self.assertRaisesRegex(ValueError, r'^go.mod contains unterminated string literal$'):
            parse_go_requirements('require "example.org/bad\\" v1.0.0\n')


if __name__ == '__main__':
    unittest.main()
