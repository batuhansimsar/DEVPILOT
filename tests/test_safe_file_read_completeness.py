"""Regular-file reads must not silently accept truncated or extra bytes."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.safe_file_read import read_bounded_regular_file


class SafeFileReadCompletenessTests(unittest.TestCase):
    def test_exact_bytes_are_returned(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'manifest.toml'
            path.write_bytes(b'hello')
            self.assertEqual(read_bounded_regular_file(path, 10), b'hello')

    def test_short_or_extra_read_with_stable_metadata_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'manifest.toml'
            path.write_bytes(b'hello')
            real_fdopen = os.fdopen

            class ModifiedReader:
                def __init__(self, stream, change):
                    self.stream = stream
                    self.change = change

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return self.stream.__exit__(*args)

                def fileno(self):
                    return self.stream.fileno()

                def read(self, size):
                    return self.change(self.stream.read(size))

            for name, change in (
                ('truncated', lambda data: data[:-1]),
                ('extra', lambda data: data + b'!'),
            ):
                with self.subTest(name=name):
                    def modified_fdopen(fd, mode):
                        return ModifiedReader(real_fdopen(fd, mode), change)

                    with patch('devpilot.safe_file_read.os.fdopen', side_effect=modified_fdopen):
                        self.assertIsNone(read_bounded_regular_file(path, 10))


if __name__ == '__main__':
    unittest.main()
