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


if __name__ == '__main__':
    unittest.main()
