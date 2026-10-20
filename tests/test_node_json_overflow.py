"""Node dependency scans must reject non-finite overflowed JSON numbers."""

import json
import tempfile
import unittest
from pathlib import Path

from devpilot.deps import scan


class NodeJSONOverflowTests(unittest.TestCase):
    def test_oversized_exponents_are_rejected_without_exposing_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for value in ('1e9999', '-1E9999'):
                with self.subTest(value=value):
                    (root / 'package.json').write_text(
                        '{"private-metadata":"secret-value","metric":' + value + '}',
                        encoding='utf-8',
                    )
                    report = scan(root)
                    self.assertEqual(report['manifests'], [])
                    self.assertEqual(len(report['warnings']), 1)
                    self.assertIn('non-finite JSON number', report['warnings'][0])
                    self.assertNotIn('secret-value', json.dumps(report))

    def test_finite_metadata_preserves_declared_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'package.json').write_text(
                '{"metric": 1.25e2, "dependencies": {"react":"^18"}}',
                encoding='utf-8',
            )
            report = scan(root)
            self.assertEqual(report['warnings'], [])
            self.assertEqual(report['totals'], {'Node.js': 1})
