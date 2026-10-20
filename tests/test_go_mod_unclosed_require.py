"""Do not silently accept incomplete Go require blocks."""

import unittest

from devpilot.go_mod import parse_go_requirements


class GoModUnclosedRequireTests(unittest.TestCase):
    def test_unterminated_require_block_has_generic_error(self):
        source = ('require example.org/valid v1.0.0\n'
                  'require (\n'
                  ' example.org/private v2.0.0 // https://user:secret@example.invalid\n')
        with self.assertRaisesRegex(ValueError, '^go.mod contains unterminated require block$') as caught:
            parse_go_requirements(source)
        self.assertNotIn('secret', str(caught.exception))
        self.assertNotIn('private', str(caught.exception))

    def test_closed_require_block_is_reported(self):
        source = ('require example.org/single v1.0.0\n'
                  'require (\n'
                  ' example.org/in-block v2.0.0\n'
                  ')\n')
        self.assertEqual(parse_go_requirements(source),
                         ['example.org/in-block', 'example.org/single'])

    def test_unterminated_empty_block_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unterminated require block'):
            parse_go_requirements('require (\n')


if __name__ == '__main__':
    unittest.main()
