"""Guard the testthat scanner against links to external suite entries."""

import tempfile
import unittest
from pathlib import Path

from devpilot.r_tests import r_test_command


class LinkedRSuiteEntriesTests(unittest.TestCase):
    def test_linked_helpers_and_other_entries_rejected(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external:
            root = Path(directory)
            (root / 'analysis.Rproj').touch()
            (root / 'DESCRIPTION').write_text('Package: example\n', encoding='utf-8')
            suite = root / 'tests' / 'testthat'
            suite.mkdir(parents=True)
            (root / 'tests' / 'testthat.R').touch()
            (suite / 'test-local.R').touch()
            names = {'analysis.Rproj'}
            self.assertIsNotNone(r_test_command(root, names))
            for filename in ('helper-external.r', 'setup-external.r', 'data-external.json'):
                with self.subTest(filename=filename):
                    linked = suite / filename
                    try:
                        linked.symlink_to(Path(external) / 'outside.r')
                    except (OSError, NotImplementedError):
                        self.skipTest('Symlinks unavailable')
                    self.assertIsNone(r_test_command(root, names))
                    linked.unlink()
                    self.assertIsNotNone(r_test_command(root, names))


if __name__ == '__main__':
    unittest.main()
