"""The standalone dependency inventory must not interpret repository text as terminal controls."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.deps import main


class DependencyTerminalSafetyTests(unittest.TestCase):
    hostile = 'unsafe\x1b[31m\n\u202e'

    def _report(self):
        return {
            'root': self.hostile,
            'manifests': [{
                'ecosystem': 'Node.js',
                'path': self.hostile,
                'count': 1,
                'groups': {self.hostile: [self.hostile]},
            }],
            'warnings': [self.hostile],
            'truncated': False,
            'totals': {'Node.js': 1},
        }

    def _run(self, *arguments):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(list(arguments))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_human_output_escapes_untrusted_paths_packages_and_warnings(self):
        with patch('devpilot.deps.scan', return_value=self._report()):
            code, output, error = self._run('--path', '.')
        self.assertEqual(code, 1)
        self.assertEqual(error, '')
        self.assertNotIn('\x1b', output)
        self.assertNotIn('\u202e', output)
        self.assertIn(r'\u001b', output)
        self.assertIn(r'\u000a', output)
        self.assertIn(r'\u202e', output)

    def test_json_output_remains_valid_and_escapes_bidi(self):
        report = self._report()
        with patch('devpilot.deps.scan', return_value=report):
            code, output, error = self._run('--path', '.', '--json')
        self.assertEqual(code, 1)
        self.assertEqual(error, '')
        self.assertNotIn('\x1b', output)
        self.assertNotIn('\u202e', output)
        self.assertIn(r'\u202e', output)
        self.assertEqual(json.loads(output), report)

    def test_argument_errors_are_safe_on_stderr(self):
        with patch('devpilot.deps.scan', side_effect=OSError(self.hostile)):
            code, output, error = self._run('--path', '.')
        self.assertEqual(code, 2)
        self.assertEqual(output, '')
        self.assertNotIn('\x1b', error)
        self.assertNotIn('\u202e', error)
        self.assertIn(r'\u001b', error)

    def test_real_manifest_dependency_name_is_rejected_without_echoing_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'package.json').write_text(
                json.dumps({'dependencies': {self.hostile: '^1.0'}}), encoding='utf-8',
            )
            code, output, error = self._run('--path', directory)
        self.assertEqual(code, 1)
        self.assertEqual(error, '')
        self.assertNotIn('\x1b', output)
        self.assertNotIn('\u202e', output)
        self.assertNotIn(self.hostile, output)
        self.assertIn('invalid package name', output)


if __name__ == '__main__':
    unittest.main()
