"""Bound package-name parsing in untrusted uv lockfiles."""

import unittest

from devpilot.uv_lock import parse_uv_lock

MAX_PACKAGE_NAME_LENGTH = 214


class UvLockNameLengthTests(unittest.TestCase):
    def test_accepts_name_at_upper_bound(self):
        name = "a" * MAX_PACKAGE_NAME_LENGTH
        self.assertEqual(parse_uv_lock(f'[[package]]\nname = "{name}"\n'), [name])

    def test_rejects_name_over_upper_bound_without_reflecting_it(self):
        name = "sensitive" + "a" * (MAX_PACKAGE_NAME_LENGTH - 8 + 1)
        with self.assertRaises(ValueError) as raised:
            parse_uv_lock(f'[[package]]\nname = "{name}"\n')
        self.assertNotIn(name, str(raised.exception))
        self.assertNotIn("sensitive", str(raised.exception))

    def test_rejects_oversized_later_record_instead_of_partial_inventory(self):
        content = ('[[package]]\nname = "valid"\n'
                   '[[package]]\nname = "' + "x" * (MAX_PACKAGE_NAME_LENGTH + 1) + '"\n')
        with self.assertRaisesRegex(ValueError, 'uv.lock packages must be tables'):
            parse_uv_lock(content)


if __name__ == "__main__":
    unittest.main()
