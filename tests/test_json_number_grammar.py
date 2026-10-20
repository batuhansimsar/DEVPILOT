"""Direct float parsing must use JSON grammar instead of Python float grammar."""

import unittest

from devpilot.json_numbers import parse_finite_json_float


class StrictJSONNumberGrammarTests(unittest.TestCase):
    def test_accepts_json_number_forms(self):
        for value, expected in (
            ('0', 0.0), ('-0', -0.0), ('123', 123.0),
            ('-12.50', -12.5), ('1e+3', 1000.0),
            ('0.3E-1', 0.03), ('1e-9999', 0.0),
        ):
            with self.subTest(value=value):
                self.assertEqual(parse_finite_json_float(value), expected)

    def test_rejects_python_only_numeric_forms_and_secret_text(self):
        for value in (
            '+1', '.5', '-.5', '1.', '01', '-01', '1_000',
            ' 1', '1 ', '0x10', '1e', '1e+', '--1',
            'private-token=+1', '', '\n0',
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, '^invalid JSON number$') as raised:
                    parse_finite_json_float(value)
                self.assertNotIn(value or 'private-token', str(raised.exception))

    def test_nonfinite_overflow_is_redacted(self):
        with self.assertRaisesRegex(ValueError, '^non-finite JSON number$'):
            parse_finite_json_float('9e9999')


if __name__ == '__main__':
    unittest.main()
