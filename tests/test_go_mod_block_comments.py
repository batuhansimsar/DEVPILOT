"""Regression coverage for Go module line and block comments."""
import unittest
from devpilot.go_mod import parse_go_requirements


class GoModuleCommentTests(unittest.TestCase):
    def test_block_comment_between_require_tokens(self):
        content = ('require /* note */ github.com/acme/one /* note */ v1.0.0 /* indirect */\n'
                   'require /* docs */ (\n'
                   '  github.com/acme/two v2.0.0 /* indirect */\n'
                   ')\n')
        self.assertEqual(parse_go_requirements(content),
                         ['github.com/acme/one', 'github.com/acme/two'])

    def test_multiline_comments_never_create_or_join_declarations(self):
        content = ('/*\nrequire github.com/evil/fake v9.9.9\n*/\n'
                   'require (\n'
                   'github.com/acme/real v1.0.0 /* comment\n'
                   'require github.com/evil/also-fake v9.9.9\n'
                   '*/\n'
                   'github.com/acme/second v1.0.0\n)\n'
                   'require github.com/acme/third /* between\nlines */ v1.0.0\n')
        self.assertEqual(parse_go_requirements(content),
                         ['github.com/acme/real', 'github.com/acme/second'])

    def test_comment_markers_within_quotes_are_not_parsed_as_comments(self):
        content = ('require "github.com/acme/normal" "v1.0.0" // indirect\n'
                   'require "github.com/acme/invalid/*name*/" v1.0.0\n'
                   'require `github.com/acme/invalid//name` v1.0.0\n')
        self.assertEqual(parse_go_requirements(content), ['github.com/acme/normal'])

    def test_unclosed_block_comment_fails_closed(self):
        self.assertEqual(parse_go_requirements(
            'require github.com/acme/first v1.0.0\n/* unfinished\n'
            'require github.com/acme/fake v1.0.0\n'), [])

    def test_line_comment_does_not_consume_next_entry(self):
        content = ('require github.com/acme/one v1.0.0 // indirect\n'
                   'require github.com/acme/two v2.0.0\n')
        self.assertEqual(parse_go_requirements(content),
                         ['github.com/acme/one', 'github.com/acme/two'])


if __name__ == '__main__':
    unittest.main()
