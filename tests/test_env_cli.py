"""Command-facing environment diagnostics do not expose secret values."""

import tempfile
import unittest
from pathlib import Path

from devpilot.env_cli import environment_status, format_environment


class EnvironmentCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_no_template_is_advisory(self):
        result, ok = environment_status(self.root)
        self.assertTrue(ok)
        self.assertIn('no .env.example', format_environment(result))

    def test_absent_local_file_is_advisory(self):
        (self.root / '.env.example').write_text('TOKEN=example-secret\n')
        result, ok = environment_status(self.root)
        self.assertTrue(ok)
        self.assertEqual(result['status'], 'local_absent')
        self.assertNotIn('example-secret', format_environment(result))

    def test_missing_key_fails_and_never_outputs_values(self):
        (self.root / '.env.example').write_text('API_SECRET=example-value\nTOKEN=abc\n')
        (self.root / '.env').write_text('TOKEN=real-secret\n')
        result, ok = environment_status(self.root)
        self.assertFalse(ok)
        self.assertIn('API_SECRET', format_environment(result))
        self.assertNotIn('example-value', format_environment(result))
        self.assertNotIn('real-secret', format_environment(result))

    def test_matching_keys_pass(self):
        (self.root / '.env.example').write_text('API_KEY=dummy\n')
        (self.root / '.env').write_text('API_KEY=real-secret\n')
        result, ok = environment_status(self.root)
        self.assertTrue(ok)
        self.assertIn('all 1 names', format_environment(result))
        self.assertNotIn('real-secret', format_environment(result))

    def test_symlinked_template_reports_failure(self):
        (self.root / 'outside').write_text('TOKEN=external-secret\n')
        try:
            (self.root / '.env.example').symlink_to(self.root / 'outside')
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        result, ok = environment_status(self.root)
        self.assertFalse(ok)
        self.assertEqual(result['status'], 'unreadable_template')
        self.assertNotIn('external-secret', format_environment(result))


if __name__ == '__main__':
    unittest.main()
