"""Regression tests for bounded package.json floating-point parsing."""

import tempfile
import unittest
from pathlib import Path

from devpilot.json_numbers import MAX_JSON_FLOAT_CHARS
from devpilot.manifest import read_package_json


class ManifestFloatLimitsTests(unittest.TestCase):
    def test_rejects_oversized_decimal_without_reflecting_value(self):
        with tempfile.TemporaryDirectory() as directory:
            secret = 'private-secret'
            decimal = '1.' + '0' * MAX_JSON_FLOAT_CHARS
            Path(directory, 'package.json').write_text(
                '{"credential":"' + secret + '","ratio":' + decimal + '}',
                encoding='utf-8',
            )
            parsed, error = read_package_json(Path(directory))
        self.assertIsNone(parsed)
        self.assertEqual(error, 'Invalid package.json: JSON exceeds parser limits')
        self.assertNotIn(secret, error)

    def test_normal_decimals_and_exponents_remain_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'package.json').write_text(
                '{"a":1.25e2,"b":-0.125,"c":1e-999}', encoding='utf-8')
            parsed, error = read_package_json(Path(directory))
        self.assertIsNone(error)
        self.assertEqual(parsed, {'a': 125.0, 'b': -0.125, 'c': 0.0})

    def test_overflow_decimal_remains_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'package.json').write_text('{"a":1e9999}', encoding='utf-8')
            parsed, error = read_package_json(Path(directory))
        self.assertIsNone(parsed)
        self.assertEqual(error, 'Invalid package.json: JSON exceeds parser limits')


if __name__ == '__main__':
    unittest.main()
