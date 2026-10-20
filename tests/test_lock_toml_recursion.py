"""Malformed deeply nested TOML must not crash direct lockfile consumers."""

import unittest

from devpilot.poetry_lock import parse_poetry_lock
from devpilot.uv_lock import parse_uv_lock


class DeeplyNestedLockfileTests(unittest.TestCase):
    def test_deep_toml_arrays_fail_closed_without_exposing_sources(self):
        # Deeper than CPython's default parser recursion limit, but small
        # enough to fit within the dependency scanner's size budget.
        nested = '[' * 1500 + '"secret"' + ']' * 1500
        for parse, kind in ((parse_poetry_lock, 'poetry.lock'),
                            (parse_uv_lock, 'uv.lock')):
            with self.subTest(kind=kind):
                source = ('[[package]]\nname = "safe"\n'
                          'source = "https://user:secret@example.invalid"\n'
                          f'nested = {nested}\n')
                with self.assertRaisesRegex(ValueError, f'invalid {kind} TOML') as raised:
                    parse(source)
                self.assertNotIn('secret', str(raised.exception))
                self.assertIsNone(raised.exception.__cause__)

    def test_normal_lockfiles_remain_supported(self):
        content = '[[package]]\nname = "My_Pkg"\nversion = "1.2.3"\n'
        self.assertEqual(parse_poetry_lock(content), ['my-pkg'])
        self.assertEqual(parse_uv_lock(content), ['my-pkg'])


if __name__ == '__main__':
    unittest.main()
