"""Ruby gems may be defined by a gemspec without a Gemfile."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from devpilot.workspaces import discover_workspaces


class GemspecWorkspaceTests(unittest.TestCase):
    def test_gemspec_only_workspace_at_root_and_nested_directory(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'my_library.gemspec').write_text('')
            nested = root / 'packages' / 'other'
            nested.mkdir(parents=True)
            (nested / 'other.GEMSPEC').write_text('')
            report = discover_workspaces(root)
        self.assertEqual(report['workspace_count'], 2)
        self.assertEqual(
            [(workspace['path'], workspace['ecosystems']) for workspace in report['workspaces']],
            [('.', ['Ruby']), ('packages/other', ['Ruby'])],
        )
        self.assertEqual(report['workspaces'][0]['manifests'],
                         [{'file': 'my_library.gemspec', 'ecosystem': 'Ruby'}])

    def test_gemspec_is_not_duplicated_when_gemfile_is_present(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'Gemfile').write_text('')
            (root / 'my_library.gemspec').write_text('')
            report = discover_workspaces(root)
        self.assertEqual(report['workspace_count'], 1)
        self.assertEqual(report['workspaces'][0]['ecosystems'], ['Ruby'])
        self.assertEqual([entry['file'] for entry in report['workspaces'][0]['manifests']],
                         ['Gemfile', 'my_library.gemspec'])

    def test_gemspec_symlink_is_not_followed(self):
        with TemporaryDirectory() as temp, TemporaryDirectory() as outside:
            root = Path(temp)
            real = Path(outside) / 'private.gemspec'
            real.write_text('')
            try:
                (root / 'private.gemspec').symlink_to(real)
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks are unavailable')
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
