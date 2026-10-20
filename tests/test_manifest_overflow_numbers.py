"""JSON package manifests must reject numeric overflows without leaking values."""

import tempfile
import unittest
from pathlib import Path

from devpilot.manifest import read_package_json


class ManifestOverflowTests(unittest.TestCase):
    def test_overflowing_exponents_are_rejected_at_any_nesting_level(self):
        payloads = (
            '{"size": 1e999}',
            '{"metadata": {"private-token": -1E999}}',
            '{"list": [1.5e309], "scripts": {"test": "echo ok"}}',
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for payload in payloads:
                with self.subTest(payload=payload):
                    (root / 'package.json').write_text(payload, encoding='utf-8')
                    parsed, error = read_package_json(root)
                    self.assertIsNone(parsed)
                    self.assertEqual(error, 'Invalid package.json: JSON exceeds parser limits')
                    self.assertNotIn('private-token', error)

    def test_finite_fractional_and_exponent_numbers_remain_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'package.json').write_text(
                '{"float": -1.25, "large": 1e300, "small": 1.5e-3}',
                encoding='utf-8',
            )
            self.assertEqual(read_package_json(root), (
                {'float': -1.25, 'large': 1e300, 'small': 0.0015}, None,
            ))


if __name__ == '__main__':
    unittest.main()
