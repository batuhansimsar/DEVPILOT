"""Reject overly long uv.lock names without echoing untrusted metadata."""

import unittest

from devpilot.uv_lock import parse_uv_lock


class UvLockNameLimitTests(unittest.TestCase):
    def test_longest_supported_name_is_inventory_safe(self):
        name = 'A' + 'b' * 213
        self.assertEqual(parse_uv_lock(f'[[package]]\nname = "{name}"\n'), [name.lower()])

    def test_overlong_name_fails_closed_without_leaking_source(self):
        name = 'a' * 215
        lock = (f'[[package]]\nname = "{name}"\n'
                'source = { registry = "https://user:private-token@example.invalid/simple" }\n')
        with self.assertRaisesRegex(ValueError, 'valid names') as captured:
            parse_uv_lock(lock)
        self.assertNotIn(name, str(captured.exception))
        self.assertNotIn('private-token', str(captured.exception))

    def test_invalid_second_entry_does_not_return_partial_inventory(self):
        content = ('[[package]]\nname = "requests"\n'
                   '[[package]]\nname = "' + 'a' * 215 + '"\n')
        with self.assertRaises(ValueError):
            parse_uv_lock(content)


if __name__ == '__main__':
    unittest.main()
