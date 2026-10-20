"""JSON manifest float decoding must not silently accept infinity."""

import json
import unittest

from devpilot.json_numbers import parse_finite_json_float


class FiniteJSONFloatTests(unittest.TestCase):
    def test_rejects_overflowing_exponents_without_echoing_values(self):
        for value in ('1e9999', '-1E9999', '9.9e9999'):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'non-finite JSON number') as caught:
                    json.loads('{"private-token": "secret", "metric": ' + value + '}',
                               parse_float=parse_finite_json_float)
                self.assertNotIn('secret', str(caught.exception))
                self.assertNotIn(value, str(caught.exception))

    def test_accepts_finite_numbers(self):
        result = json.loads('{"a": 1.25e2, "b": -0.5, "c": 1e-9999}',
                            parse_float=parse_finite_json_float)
        self.assertEqual(result, {'a': 125.0, 'b': -0.5, 'c': 0.0})

    def test_direct_invalid_input_does_not_expose_secret(self):
        for value in ('private-token:supersecret', 'abc\\x00credential', ''):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, '^invalid JSON number$') as raised:
                    parse_finite_json_float(value)
                if value:
                    self.assertNotIn(value, str(raised.exception))
                self.assertNotIn('secret', str(raised.exception))


    def test_rejects_python_float_spellings_not_valid_in_json(self):
        invalid = ('+1', '01', '-01', '.5', '1.', '1_000', ' 1', '1\\n',
                   '1e', '1e+', '--1', '0x10', 'inf', 'nan')
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, '^invalid JSON number$') as caught:
                    parse_finite_json_float(value)
                self.assertNotIn(value, str(caught.exception))

    def test_direct_valid_json_spellings(self):
        cases = {'0': 0.0, '-0': -0.0, '1': 1.0, '-1.25': -1.25,
                 '1e+2': 100.0, '1E-2': 0.01, '10.0': 10.0}
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(parse_finite_json_float(value), expected)

    def test_non_string_direct_input_is_safely_rejected(self):
        for value in (None, 1, True, b'1'):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, '^invalid JSON number$'):
                    parse_finite_json_float(value)


if __name__ == '__main__':
    unittest.main()
