"""Python test command discovery must not cross linked project roots."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.python_tests import python_test_command


class PythonTestRootPathSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / 'project'
        self.project.mkdir()
        tests = self.project / 'tests'
        tests.mkdir()
        (tests / 'test_example.py').touch()

    def symlink(self, link: Path, target: Path):
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')

    def test_direct_linked_root_refused_for_both_runners(self):
        link = self.base / 'project-link'
        self.symlink(link, self.project)
        for pytest_available in (True, False):
            with self.subTest(pytest_available=pytest_available), patch(
                'devpilot.python_tests.PathFinder.find_spec',
                return_value=object() if pytest_available else None,
            ):
                self.assertIsNone(python_test_command(link))

    def test_linked_ancestor_refused_for_both_runners(self):
        link = self.base / 'parent-link'
        self.symlink(link, self.base)
        project_via_link = link / 'project'
        for pytest_available in (True, False):
            with self.subTest(pytest_available=pytest_available), patch(
                'devpilot.python_tests.PathFinder.find_spec',
                return_value=object() if pytest_available else None,
            ):
                self.assertIsNone(python_test_command(project_via_link))

    def test_regular_root_still_selects_runners(self):
        with patch('devpilot.python_tests.PathFinder.find_spec', return_value=object()):
            self.assertEqual(python_test_command(self.project)['argv'][-2:], ['pytest', 'tests'])
        with patch('devpilot.python_tests.PathFinder.find_spec', return_value=None):
            self.assertEqual(python_test_command(self.project)['argv'][-4:],
                             ['unittest', 'discover', '-s', 'tests'])


if __name__ == '__main__':
    unittest.main()
