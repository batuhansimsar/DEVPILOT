"""Match workspace discovery for Mix lockfile-only projects."""

import tempfile
import unittest
from pathlib import Path

from devpilot.core import detect_projects, test_commands
from devpilot.workspaces import discover_workspaces


class ElixirLockfileConsistencyTests(unittest.TestCase):
    def test_lockfile_only_is_detected_but_not_executed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'mix.lock').write_text('%{}\n')
            self.assertIn('Elixir', detect_projects(root))
            self.assertEqual(discover_workspaces(root)['workspaces'][0]['ecosystems'], ['Elixir'])
            self.assertNotIn('Elixir', [entry['ecosystem'] for entry in test_commands(root)])

    def test_symlinked_mix_lockfile_is_not_detection_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'mix.lock.bak').write_text('%{}\n')
            try:
                (root / 'mix.lock').symlink_to(root / 'mix.lock.bak')
            except (OSError, NotImplementedError):
                self.skipTest('Symlinks unavailable')
            self.assertNotIn('Elixir', detect_projects(root))
            self.assertEqual(discover_workspaces(root)['workspace_count'], 0)


if __name__ == '__main__':
    unittest.main()
