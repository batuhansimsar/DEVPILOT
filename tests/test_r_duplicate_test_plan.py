"""Prevent duplicate R test commands in polyglot workspaces."""

import tempfile
import unittest
from pathlib import Path

from devpilot.core import test_commands


class RNoDuplicateCommandsTests(unittest.TestCase):
    def test_r_testthat_is_discovered_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'renv.lock').write_text('{}')
            (root / 'DESCRIPTION').write_text('Package: sample\n')
            (root / 'tests' / 'testthat').mkdir(parents=True)
            (root / 'tests' / 'testthat.R').touch()
            (root / 'tests' / 'testthat' / 'test-a.R').touch()
            (root / 'go.mod').write_text('module example.org/sample\n\ngo 1.23\n')
            commands = test_commands(root)
            self.assertEqual([c['ecosystem'] for c in commands].count('R'), 1)
            self.assertEqual([c['ecosystem'] for c in commands].count('Go'), 1)
            self.assertEqual([c['argv'] for c in commands if c['ecosystem'] == 'R'],
                             [['Rscript', '-e', 'testthat::test_local()']])


if __name__ == '__main__':
    unittest.main()
