"""Regression tests for tracked dotenv names beyond the .env prefix."""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.security import tracked_environment_files


class NamedEnvironmentSecurityTests(unittest.TestCase):
    def test_staged_named_dotenv_files_and_safe_templates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            names = (
                '.env', 'backend/.env.production', 'backend/service.env',
                'frontend/service.env.production', 'frontend/service.env.example.local',
                'frontend/service.env.template', 'frontend/service.env.production.sample',
                'frontend/.environment', 'frontend/main.py',
            )
            for name in names:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('PRIVATE_VALUE_NOT_TO_REPORT', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '-f', '--all'], check=True)
            result = tracked_environment_files(root)
            self.assertEqual(result, [
                '.env', 'backend/.env.production', 'backend/service.env',
                'frontend/service.env.example.local', 'frontend/service.env.production',
            ])
            self.assertNotIn('PRIVATE_VALUE_NOT_TO_REPORT', repr(result))

    def test_fails_closed_on_torn_index(self):
        with patch('devpilot.security._tracked_paths', return_value=b'backend/service.env'):
            self.assertEqual(tracked_environment_files(Path('.')), [])

    def test_non_utf8_name_remains_safe(self):
        with patch('devpilot.security._tracked_paths', return_value=b'backend/service.env.\\xff\\0'):
            self.assertEqual(tracked_environment_files(Path('.')), ['backend/service.env.\\\\udcff'])


if __name__ == '__main__':
    unittest.main()
