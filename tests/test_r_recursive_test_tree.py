"""Nested helpers and fixtures must not escape the selected R project."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.r_tests import r_test_command


class RecursiveRTestSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'sample.Rproj').touch()
        (self.root / 'DESCRIPTION').write_text('Package: sample\n', encoding='utf-8')
        self.suite = self.root / 'tests' / 'testthat'
        self.suite.mkdir(parents=True)
        (self.root / 'tests' / 'testthat.R').touch()
        (self.suite / 'test-example.R').touch()

    def discover(self):
        return r_test_command(self.root, {'sample.Rproj'})

    def test_nested_regular_helpers_are_allowed(self):
        helpers = self.suite / 'fixtures' / 'nested'
        helpers.mkdir(parents=True)
        (helpers / 'sample.csv').write_text('x,y\n1,2\n', encoding='utf-8')
        self.assertIsNotNone(self.discover())

    def test_nested_symlinked_helper_rejects_suite(self):
        helpers = self.suite / 'fixtures' / 'nested'
        helpers.mkdir(parents=True)
        try:
            (helpers / 'linked.csv').symlink_to(self.suite / 'test-example.R')
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.assertIsNone(self.discover())

    def test_sibling_fixture_symlink_rejects_suite(self):
        data = self.root / 'tests' / 'fixtures'
        data.mkdir()
        try:
            (data / 'link').symlink_to(self.suite, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.assertIsNone(self.discover())

    def test_unreadable_nested_directory_fails_closed(self):
        helpers = self.suite / 'helpers'
        helpers.mkdir()
        original_iterdir = Path.iterdir

        def patched_iterdir(path):
            if path == helpers:
                raise PermissionError('private file path')
            return original_iterdir(path)

        with patch.object(Path, 'iterdir', patched_iterdir):
            self.assertIsNone(self.discover())

    def test_nested_test_file_alone_is_not_a_discovered_suite(self):
        (self.suite / 'test-example.R').unlink()
        nested = self.suite / 'fixtures'
        nested.mkdir()
        (nested / 'test-not-a-suite.R').touch()
        self.assertIsNone(self.discover())

    def test_tree_scan_has_global_entry_limit(self):
        from devpilot import r_tests
        nested = self.suite / 'fixtures'
        nested.mkdir()
        for i in range(4):
            (nested / f'helper-{i}.R').touch()
        with patch.object(r_tests, '_MAX_R_SUITE_ENTRIES', 5):
            self.assertIsNone(self.discover())

    def test_special_file_rejected_when_supported(self):
        import os
        if not hasattr(os, 'mkfifo'):
            self.skipTest('FIFOs unavailable')
        fifo = self.suite / 'pipe'
        try:
            os.mkfifo(fifo)
        except OSError:
            self.skipTest('FIFOs unavailable')
        self.assertIsNone(self.discover())


if __name__ == '__main__':
    unittest.main()
