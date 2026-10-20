"""Tracked .env discovery shares the capped, fail-closed Git index reader."""

import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.security import tracked_environment_files


class EnvironmentIndexLimitTests(unittest.TestCase):
    def test_reuses_capped_reader_and_filters_non_environment_paths(self):
        with patch('devpilot.security._tracked_paths', return_value=b'src/main.py\0API/.ENV.local\0.env.example\0') as reader:
            self.assertEqual(tracked_environment_files(Path('.')), ['API/.ENV.local'])
        reader.assert_called_once_with(Path('.'))

    def test_malformed_index_is_not_accepted_as_complete(self):
        for output in (b'.env', b'\0.env\0', b'.env\0\0', b'README\0.env'):
            with self.subTest(output=output), patch('devpilot.security._tracked_paths', return_value=output):
                self.assertEqual(tracked_environment_files(Path('.')), [])

    def test_path_limit_cannot_be_bypassed_by_reader_mock(self):
        with patch('devpilot.security._tracked_paths', return_value=b'a\0' * 100_001 + b'.env\0'):
            self.assertEqual(tracked_environment_files(Path('.')), [])

    def test_reader_errors_are_reported_as_empty_for_backwards_compatibility(self):
        with patch('devpilot.security._tracked_paths', side_effect=RuntimeError('bad index')):
            self.assertEqual(tracked_environment_files(Path('.')), [])


if __name__ == '__main__':
    unittest.main()
