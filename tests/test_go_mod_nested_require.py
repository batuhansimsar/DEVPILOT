"""Nested Go require blocks must not produce a partial inventory."""

import unittest

from devpilot.go_mod import parse_go_requirements


class GoModNestedRequireTests(unittest.TestCase):
    def test_nested_require_blocks_are_rejected_without_leaking_paths(self):
        for nested in ('require (', 'require(', 'require\t (', 'require /*comment*/ ('):
            with self.subTest(nested=nested):
                source = ('require (\n'
                          ' example.org/visible v1.0.0\n'
                          f' {nested} // https://user:secret@example.invalid\n'
                          ' example.org/private v2.0.0\n'
                          ')\n)\n')
                with self.assertRaisesRegex(ValueError, '^go.mod contains nested require block$') as caught:
                    parse_go_requirements(source)
                self.assertNotIn('secret', str(caught.exception))
                self.assertNotIn('private', str(caught.exception))

    def test_two_separate_blocks_still_work(self):
        source = ('require (\n example.org/one v1.0.0\n)\n'
                  'require /*comment*/ (\n example.org/two v2.0.0\n)\n')
        self.assertEqual(parse_go_requirements(source), ['example.org/one', 'example.org/two'])

    def test_module_named_require_is_not_mistaken_for_nested_block(self):
        self.assertEqual(parse_go_requirements('require (\n require v1.0.0\n)\n'), ['require'])


if __name__ == '__main__':
    unittest.main()
