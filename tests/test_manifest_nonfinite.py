"""Package metadata must be strict JSON, not Python's permissive extension."""

import json
import tempfile
import unittest
from pathlib import Path

from devpilot.manifest import read_package_json


class StrictManifestTests(unittest.TestCase):
    def test_nonfinite_numeric_literals_are_rejected_without_echoing_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / 'package.json'
            for value in ('NaN', 'Infinity', '-Infinity'):
                with self.subTest(value=value):
                    manifest.write_text('{"internalSecret": "do-not-log", "metric": ' + value + '}')
                    result, error = read_package_json(root)
                    self.assertIsNone(result)
                    self.assertIsNotNone(error)
                    self.assertIn('Invalid package.json', error)
                    self.assertNotIn('do-not-log', error)

    def test_ordinary_json_package_metadata_still_parses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            expected = {'name': 'example', 'scripts': {'test': 'echo ok'}, 'count': 0}
            (root / 'package.json').write_text(json.dumps(expected))
            self.assertEqual(read_package_json(root), (expected, None))

    def test_absent_manifest_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(read_package_json(Path(tmp)), (None, None))


if __name__ == '__main__':
    unittest.main()
