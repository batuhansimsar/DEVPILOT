"""Root .NET toolchain configuration should be detected consistently."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot import core


class DotnetRootManifestsTests(unittest.TestCase):
    def test_sdk_and_central_package_markers_are_dotnet_projects(self):
        for filename, content in (
            ('global.json', '{"sdk":{"version":"8.0.100"}}'),
            ('Directory.Packages.props', '<Project/>'),
        ):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / filename).write_text(content, encoding='utf-8')
                self.assertIn('.NET', core.detect_projects(root))
                self.assertIn(filename, core.analyze_project(root)['key_files'])
                self.assertFalse(any(command['ecosystem'] == '.NET'
                                     for command in core.test_commands(root)))
                with patch('devpilot.core.shutil.which', return_value=None):
                    self.assertIn('Missing dotnet required by detected project',
                                  core.doctor_report(root)['warnings'])

    def test_lookalike_and_symlink_markers_are_not_projects(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            (root / 'global.json.bak').write_text('{}', encoding='utf-8')
            (root / 'Directory.Packages.props.disabled').write_text('', encoding='utf-8')
            try:
                (root / 'global.json').symlink_to(Path(outside) / 'global.json')
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable on this platform')
            self.assertNotIn('.NET', core.detect_projects(root))


if __name__ == '__main__':
    unittest.main()
