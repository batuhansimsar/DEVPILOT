"""Malformed Go comments must not masquerade as an empty dependency inventory."""

import unittest

from devpilot.go_mod import parse_go_requirements


class GoModUnterminatedCommentTests(unittest.TestCase):
    def test_reports_unterminated_comment_instead_of_silent_empty_result(self):
        source = ('module example.org/project\n'
                  'require example.org/valid v1.0.0\n'
                  '/* private https://user:secret@example.invalid')
        with self.assertRaisesRegex(ValueError, '^go.mod contains unterminated block comment$') as caught:
            parse_go_requirements(source)
        self.assertNotIn('secret', str(caught.exception))

    def test_closed_comment_still_ignores_fake_requirements(self):
        source = ('require example.org/real v1.0.0\n'
                  '/* require example.org/fake v9.0.0 */\n'
                  'require example.org/other v2.0.0\n')
        self.assertEqual(parse_go_requirements(source), ['example.org/other', 'example.org/real'])

    def test_comment_markers_inside_quoted_tokens_are_not_block_comments(self):
        source = ('require example.org/good v1.0.0\n'
                  'require "example.org/contains/*marker" v2.0.0\n')
        self.assertEqual(parse_go_requirements(source), ['example.org/good'])


if __name__ == '__main__':
    unittest.main()
