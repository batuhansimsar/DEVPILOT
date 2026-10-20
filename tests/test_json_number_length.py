"""Oversized JSON float literals must not exhaust manifest scan resources."""

import json
import unittest
from unittest.mock import patch

from devpilot.json_numbers import MAX_JSON_FLOAT_CHARS, parse_finite_json_float


class JSONFloatLengthTests(unittest.TestCase):
    def test_rejects_oversized_json_numbers_before_float_conversion(self):
        oversized = (
            '1' * (MAX_JSON_FLOAT_CHARS + 1),
            '1e' + '0' * MAX_JSON_FLOAT_CHARS,
            '0.' + '0' * MAX_JSON_FLOAT_CHARS,
        )
        for number in oversized:
            with self.subTest(prefix=number[:2]):
                with patch('devpilot.json_numbers.float', create=True) as convert:
                    with self.assertRaisesRegex(ValueError, '^invalid JSON number$') as raised:
                        parse_finite_json_float(number)
                    convert.assert_not_called()
                self.assertNotIn(number, str(raised.exception))

    def test_accepts_boundary_length_valid_floats(self):
        valid = ('1e' + '0' * (MAX_JSON_FLOAT_CHARS - 2),
                 '0.' + '0' * (MAX_JSON_FLOAT_CHARS - 2))
        self.assertEqual(parse_finite_json_float(valid[0]), 1.0)
        self.assertEqual(parse_finite_json_float(valid[1]), 0.0)

    def test_json_decoder_uses_same_size_guard(self):
        number = '1e' + '0' * MAX_JSON_FLOAT_CHARS
        with self.assertRaisesRegex(ValueError, '^invalid JSON number$'):
            json.loads('{"value": ' + number + '}', parse_float=parse_finite_json_float)


if __name__ == '__main__':
    unittest.main()
