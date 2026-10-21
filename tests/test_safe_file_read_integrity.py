"""Incomplete manifest reads must not be accepted as genuine file contents."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.safe_file_read import read_bounded_regular_file


class ShortReadTests(unittest.TestCase):
    def test_partial_read_with_unchanged_file_metadata_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'requirements.txt'
            path.write_bytes(b'one\ntwo\n')
            fdopen = os.fdopen

            class PartialStream:
                def __init__(self, inner):
                    self.inner = inner

                def __enter__(self):
                    self.inner.__enter__()
                    return self

                def __exit__(self, *args):
                    return self.inner.__exit__(*args)

                def fileno(self):
                    return self.inner.fileno()

                def read(self, count):
                    return self.inner.read(3)

            with patch('devpilot.safe_file_read.os.fdopen',
                       side_effect=lambda fd, mode: PartialStream(fdopen(fd, mode))):
                self.assertIsNone(read_bounded_regular_file(path, 100))

            # Full reads still work, including an exact-size byte budget.
            self.assertEqual(read_bounded_regular_file(path, 8), b'one\ntwo\n')

    def test_read_uses_observed_file_size_instead_of_large_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'small.txt'
            path.write_bytes(b'abc')
            fdopen = os.fdopen
            requested_sizes = []

            class TrackingStream:
                def __init__(self, inner):
                    self.inner = inner

                def __enter__(self):
                    self.inner.__enter__()
                    return self

                def __exit__(self, *args):
                    return self.inner.__exit__(*args)

                def fileno(self):
                    return self.inner.fileno()

                def read(self, count):
                    requested_sizes.append(count)
                    return self.inner.read(count)

            with patch('devpilot.safe_file_read.os.fdopen',
                       side_effect=lambda fd, mode: TrackingStream(fdopen(fd, mode))):
                self.assertEqual(read_bounded_regular_file(path, 1_000_000_000), b'abc')
            self.assertEqual(requested_sizes, [4])

    def test_zero_length_file_with_zero_budget_is_valid(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'empty.txt'
            path.touch()
            self.assertEqual(read_bounded_regular_file(path, 0), b'')


if __name__ == '__main__':
    unittest.main()
