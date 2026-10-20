"""Regression coverage for .NET SDK and central package management workspaces."""

import tempfile
import unittest
from pathlib import Path

from devpilot.workspaces import discover_workspaces


class DotnetManifestWorkspaceTests(unittest.TestCase):
    def test_global_json_and_directory_packages_props_at_distinct_levels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'global.json').write_text('{"sdk":{"version":"8.0.100"}}')
            service = root / 'services' / 'api'
            service.mkdir(parents=True)
            (service / 'Directory.Packages.props').write_text('<Project/>')
            report = discover_workspaces(root)
        self.assertEqual(report['workspace_count'], 2)
        self.assertEqual([entry['path'] for entry in report['workspaces']], ['.', 'services/api'])
        self.assertEqual([entry['ecosystems'] for entry in report['workspaces']], [['.NET'], ['.NET']])
        self.assertEqual(report['workspaces'][1]['manifests'],
                         [{'file': 'Directory.Packages.props', 'ecosystem': '.NET'}])

    def test_does_not_count_linked_config_files_or_similarly_named_files(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            outside = Path(external) / 'global.json'
            outside.write_text('{}')
            try:
                (root / 'global.json').symlink_to(outside)
            except (NotImplementedError, OSError):
                self.skipTest('Symlinks unavailable')
            (root / 'global.json.bak').write_text('{}')
            (root / 'Directory.Packages.props.disabled').write_text('<Project/>')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
