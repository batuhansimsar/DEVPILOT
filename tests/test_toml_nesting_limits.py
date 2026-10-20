"""TOML lockfile parsers must handle excessive nesting without leaking input."""

import unittest
from unittest.mock import patch

from devpilot import poetry_lock, uv_lock


class TomlNestingLimitsTests(unittest.TestCase):
    def test_deeply_nested_toml_fails_closed(self):
        # Below the inventory's bounded file-size limit, but enough to exceed
        # the parser's recursion budget on CPython and on supported tomli.
        nested = 'metadata = ' + '{child = ' * 1000 + '1' + '}' * 1000
        for module, parser, message in (
            (uv_lock, uv_lock.parse_uv_lock, 'invalid uv.lock TOML'),
            (poetry_lock, poetry_lock.parse_poetry_lock, 'invalid poetry.lock TOML'),
        ):
            with self.subTest(parser=module.__name__):
                with self.assertRaisesRegex(ValueError, message) as captured:
                    parser('source = "https://user:secret@example.invalid"\n' + nested)
                self.assertNotIn('secret', str(captured.exception))

    def test_recursion_error_never_exposes_parser_input(self):
        for module, parser, message in (
            (uv_lock, uv_lock.parse_uv_lock, 'invalid uv.lock TOML'),
            (poetry_lock, poetry_lock.parse_poetry_lock, 'invalid poetry.lock TOML'),
        ):
            with self.subTest(parser=module.__name__):
                with patch.object(module.tomllib, 'loads', side_effect=RecursionError('secret-key')):
                    with self.assertRaisesRegex(ValueError, message) as captured:
                        parser('secret-key')
                self.assertNotIn('secret-key', str(captured.exception))
                self.assertTrue(captured.exception.__suppress_context__)

    def test_normal_package_inventory_unchanged(self):
        lock = '[[package]]\nname = "My_Pkg"\nversion = "1.0"\n'
        self.assertEqual(uv_lock.parse_uv_lock(lock), ['my-pkg'])
        self.assertEqual(poetry_lock.parse_poetry_lock(lock), ['my-pkg'])


if __name__ == '__main__':
    unittest.main()
