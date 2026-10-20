"""Redacted security audits must not expose host checkout locations."""

import contextlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from devpilot.secret_audit import audit, main


@unittest.skipUnless(shutil.which('git'), 'Git executable required')
class RedactedRootTests(unittest.TestCase):
    def test_redact_paths_hides_repository_root_and_sensitive_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True, capture_output=True)
            (root / '.env').write_text('TOKEN_DO_NOT_PRINT=secret', encoding='utf-8')
            subprocess.run(['git', 'add', '--', '.env'], cwd=root, check=True, capture_output=True)

            redacted = audit(root, redact_paths=True)
            self.assertEqual(redacted['path'], '<redacted>')
            self.assertEqual(redacted['tracked_files_checked'], 1)
            self.assertEqual(len(redacted['findings']), 1)
            self.assertNotIn('path', redacted['findings'][0])
            self.assertNotIn(str(root), json.dumps(redacted))
            self.assertNotIn('TOKEN_DO_NOT_PRINT', json.dumps(redacted))

            standard = audit(root)
            self.assertEqual(standard['path'], str(root.resolve()))
            self.assertEqual(standard['findings'][0]['path'], '.env')

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main([str(root), '--json', '--redact-paths'])
            self.assertEqual(exit_code, 1)
            self.assertEqual(json.loads(stdout.getvalue())['path'], '<redacted>')
            self.assertNotIn(str(root), stdout.getvalue())

    def test_clean_index_also_redacts_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True, capture_output=True)
            report = audit(root, redact_paths=True)
            self.assertTrue(report['ok'])
            self.assertEqual(report['tracked_files_checked'], 0)
            self.assertEqual(report['path'], '<redacted>')


if __name__ == '__main__':
    unittest.main()
