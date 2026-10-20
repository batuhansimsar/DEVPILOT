"""Ensure hostile deeply nested manifests cannot crash dependency scans."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from devpilot.deps import main, scan


class DeepManifestTests(unittest.TestCase):
    def test_nested_json_reports_warning_and_keeps_other_manifests(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'package.json').write_text(
                '{"dependencies":' + '[' * 12000 + '0' + ']' * 12000 + '}',
                encoding='utf-8',
            )
            (root / 'requirements.txt').write_text('requests>=2\n', encoding='utf-8')
            report = scan(root)
            self.assertEqual(len(report['warnings']), 1)
            self.assertIn('package.json: manifest nesting exceeds parser limits', report['warnings'][0])
            self.assertEqual(report['totals'], {'Python': 1})
            self.assertEqual(report['manifests'][0]['groups']['requirements'], ['requests'])

    def test_cli_emits_valid_json_and_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'package.json').write_text(
                '{"dependencies":' + '[' * 12000 + '0' + ']' * 12000 + '}',
                encoding='utf-8',
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = main(['--path', str(root), '--json'])
            self.assertEqual(exit_code, 1)
            report = json.loads(output.getvalue())
            self.assertEqual(len(report['warnings']), 1)
            self.assertEqual(report['manifests'], [])


if __name__ == '__main__':
    unittest.main()
