"""Guard read sizes and partial reads when inspecting untrusted manifests."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.safe_file_read import read_bounded_regular_file


class _ObservedStream:
    def __init__(self, stream, requested_sizes, *, shorten=False):
        self.stream = stream
        self.requested_sizes = requested_sizes
        self.shorten = shorten

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self.stream.__exit__(*args)

    def fileno(self):
        return self.stream.fileno()

    def read(self, size):
        self.requested_sizes.append(size)
        # This cap prevents an outdated implementation from exhausting memory
        # during its regression test if it accidentally requests sys.maxsize.
        result = self.stream.read(min(size, 4096))
        return result[:-1] if self.shorten else result


class BoundedReadAllocationTests(unittest.TestCase):
    def _inspect_with_observed_reader(self, path, budget, *, shorten=False):
        requests = []
        real_fdopen = os.fdopen

        def tracked_fdopen(fd, mode):
            return _ObservedStream(real_fdopen(fd, mode), requests, shorten=shorten)

        with patch('devpilot.safe_file_read.os.fdopen', side_effect=tracked_fdopen):
            result = read_bounded_regular_file(path, budget)
        return result, requests

    def test_large_budget_does_not_request_huge_read_for_small_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'small.toml'
            path.write_bytes(b'abc')
            result, requests = self._inspect_with_observed_reader(path, sys.maxsize - 1)
            self.assertEqual(result, b'abc')
            self.assertEqual(requests, [4])

    def test_short_read_does_not_look_like_complete_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'small.toml'
            path.write_bytes(b'abc')
            result, requests = self._inspect_with_observed_reader(path, 128, shorten=True)
            self.assertIsNone(result)
            self.assertEqual(requests, [4])


if __name__ == '__main__':
    unittest.main()
