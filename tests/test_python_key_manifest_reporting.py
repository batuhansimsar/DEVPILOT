"""Python project manifests should appear in the analyze key-file summary."""

import tempfile
import unittest
from pathlib import Path

from devpilot.core import analyze_project


class PythonKeyManifestReportingTests(unittest.TestCase):
    def test_setup_cfg_and_pip_tools_inputs_are_key_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('setup.cfg', 'requirements-dev.in', 'dev-requirements.txt'):
                (root / name).write_text('example\n', encoding='utf-8')
            (root / 'requirementsnotes.txt').write_text('not a manifest\n', encoding='utf-8')
            report = analyze_project(root)

        self.assertEqual(report['project_types'], ['Python'])
        self.assertEqual(
            report['key_files'],
            ['dev-requirements.txt', 'requirements-dev.in', 'setup.cfg'],
        )

    def test_nested_pip_inputs_are_not_reported_as_root_key_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / 'service'
            nested.mkdir()
            (nested / 'requirements-dev.in').write_text('pytest\n', encoding='utf-8')
            report = analyze_project(root)

        self.assertEqual(report['key_files'], [])


if __name__ == '__main__':
    unittest.main()
