"""Reject oversized PEP 751 manifests before parsing or walking packages."""

import unittest
from unittest.mock import patch

from devpilot.pylock import MAX_PYLOCK_INPUT_CHARS, MAX_PYLOCK_PACKAGES, parse_pylock


class PylockResourceBoundsTests(unittest.TestCase):
    def test_large_input_is_rejected_before_toml_parser(self):
        content = 'x' * (MAX_PYLOCK_INPUT_CHARS + 1)
        with patch('devpilot.pylock.tomllib.loads', side_effect=AssertionError('must not parse')):
            with self.assertRaisesRegex(ValueError, 'size limit'):
                parse_pylock(content)

    def test_invalid_input_type_is_rejected_privately(self):
        for value in (None, b'', 42):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_pylock(value)

    def test_oversized_package_array_is_rejected_before_walk(self):
        data = {'lock-version': '1.0', 'created-by': 'unit test',
                'packages': [None] * (MAX_PYLOCK_PACKAGES + 1)}
        with patch('devpilot.pylock.tomllib.loads', return_value=data):
            with self.assertRaisesRegex(ValueError, 'bounded array'):
                parse_pylock('lock-version = "1.0"')

    def test_valid_pylock_inventory_unchanged(self):
        content = ('lock-version = "1.0"\ncreated-by = "unit test"\n'
                   '[[packages]]\nname = "Requests"\n'
                   '[[packages]]\nname = "my_package"\n')
        self.assertEqual(parse_pylock(content), ['my-package', 'requests'])


if __name__ == '__main__':
    unittest.main()
