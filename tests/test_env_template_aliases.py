"""Regression coverage for additional safe .env template filenames."""

import tempfile
import unittest
from pathlib import Path

from devpilot.envcheck import TEMPLATES, inspect_env
from devpilot.env_cli import environment_status, format_environment


class EnvTemplateAliasesTests(unittest.TestCase):
    def test_dist_and_defaults_report_missing_keys_without_values(self):
        for name in ('.env.dist', '.env.defaults'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / name).write_text('TOKEN=sensitive-template-value\nDATABASE_URL=private\n')
                (root / '.env').write_text('TOKEN=sensitive-local-value\n')
                result, okay = environment_status(root)
                self.assertEqual(result['template'], name)
                self.assertEqual(result['missing_keys'], ['DATABASE_URL'])
                self.assertEqual(result['status'], 'missing_keys')
                self.assertFalse(okay)
                self.assertNotIn('sensitive-', str(result))
                self.assertNotIn('private', str(result))

    def test_template_priority_remains_backward_compatible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.env.example').write_text('FROM_EXAMPLE=x\n')
            (root / '.env.dist').write_text('FROM_DIST=x\n')
            (root / '.env').write_text('FROM_DIST=y\n')
            result = inspect_env(root)
            self.assertEqual(result['template'], '.env.example')
            self.assertEqual(result['missing_keys'], ['FROM_EXAMPLE'])

    def test_new_templates_are_advisory_when_local_absent(self):
        for name in ('.env.dist', '.env.defaults'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / name).write_text('TOKEN=never-output\n')
                result, okay = environment_status(root)
                self.assertTrue(okay)
                self.assertEqual(result['status'], 'local_absent')
                self.assertEqual(result['template'], name)
                self.assertNotIn('never-output', format_environment(result))

    def test_no_template_message_lists_supported_names(self):
        self.assertEqual(len(TEMPLATES), len(set(TEMPLATES)))
        message = format_environment({'status': 'no_template'})
        for name in TEMPLATES:
            self.assertIn(name, message)


if __name__ == '__main__':
    unittest.main()
