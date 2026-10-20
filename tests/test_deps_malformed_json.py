"""Invalid Node manifests must not terminate read-only dependency inventory."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from devpilot.deps import main, scan


class MalformedNodeManifestTests(unittest.TestCase):
    def test_deeply_nested_json_records_warning_without_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'package.json').write_text('{"dependencies": ' + '[' * 12000 + '0' + ']' * 12000 + '}')
            result = scan(root)
            self.assertEqual(result['manifests'], [])
            self.assertEqual(len(result['warnings']), 1)
            self.assertIn('nesting exceeds parser limits', result['warnings'][0])
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                self.assertEqual(main(['--path', str(root), '--json']), 1)
            self.assertEqual(json.loads(stream.getvalue())['warnings'], result['warnings'])

    def test_nonfinite_literals_rejected_without_echoing_manifest_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for number in ('NaN', 'Infinity', '-Infinity'):
                with self.subTest(number=number):
                    (root / 'package.json').write_text('{"secret": "do-not-echo", "metric": ' + number + '}')
                    report = scan(root)
                    self.assertEqual(report['manifests'], [])
                    self.assertIn('non-finite JSON number', report['warnings'][0])
                    self.assertNotIn('do-not-echo', json.dumps(report))

    def test_valid_package_json_still_counts_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'package.json').write_text('{"dependencies":{"react":"^18"},"private":true}')
            result = scan(root)
            self.assertEqual(result['totals'], {'Node.js': 1})
            self.assertEqual(result['warnings'], [])


if __name__ == '__main__':
    unittest.main()
