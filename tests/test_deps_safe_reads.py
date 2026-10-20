"""Regression tests for bounded, non-following dependency reads."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.deps import MAX_BYTES, _read


class SafeDependencyReads(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "requirements.txt"

    def test_regular_manifest_is_read(self):
        self.path.write_text("pytest>=8\n", encoding="utf-8")
        self.assertEqual(_read(self.path), "pytest>=8\n")

    def test_file_growth_after_stat_is_bounded(self):
        self.path.write_text("ok", encoding="utf-8")
        original = os.open

        def grow(path, flags):
            self.path.write_bytes(b"x" * (MAX_BYTES + 1))
            return original(path, flags)

        with patch("devpilot.deps.os.open", side_effect=grow):
            with self.assertRaisesRegex(ValueError, "larger"):
                _read(self.path)

    def test_preexisting_oversized_manifest_is_rejected(self):
        self.path.write_bytes(b"x" * (MAX_BYTES + 1))
        with self.assertRaisesRegex(ValueError, "larger"):
            _read(self.path)

    def test_symlink_is_rejected(self):
        self.path.symlink_to("missing.txt")
        with self.assertRaises((ValueError, OSError)):
            _read(self.path)

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "O_NOFOLLOW unavailable")
    def test_symlink_swapped_after_stat_is_not_read(self):
        self.path.write_text("ok")
        private = Path(self.temp.name) / "private.txt"
        private.write_text("do-not-read")
        original = os.open

        def swap(path, flags):
            self.path.unlink()
            self.path.symlink_to(private)
            return original(path, flags)

        with patch("devpilot.deps.os.open", side_effect=swap):
            with self.assertRaises(OSError):
                _read(self.path)

    def test_regular_file_swapped_after_stat_is_not_read(self):
        self.path.write_text("safe")
        other = Path(self.temp.name) / "other.txt"
        other.write_text("do-not-read")
        original = os.open

        def swap(path, flags):
            self.path.unlink()
            other.rename(self.path)
            return original(path, flags)

        with patch("devpilot.deps.os.open", side_effect=swap):
            with self.assertRaisesRegex(ValueError, "changed during inspection"):
                _read(self.path)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO unavailable")
    def test_named_pipe_is_rejected_without_blocking(self):
        os.mkfifo(self.path)
        with self.assertRaisesRegex(ValueError, "not a regular"):
            _read(self.path)


    def test_in_place_rewrite_during_read_is_rejected(self):
        """Even a same-size edit invalidates the manifest snapshot."""
        self.path.write_text("pytest>=8\\n", encoding="utf-8")
        original_fstat = os.fstat
        calls = 0

        def rewrite_before_post_read_stat(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                previous = self.path.stat()
                self.path.write_text("pytest>=9\\n", encoding="utf-8")
                # Ensure a detectable metadata change even on coarse filesystems.
                os.utime(self.path, ns=(previous.st_atime_ns, previous.st_mtime_ns + 2_000_000_000))
            return original_fstat(fd)

        with patch("devpilot.deps.os.fstat", side_effect=rewrite_before_post_read_stat):
            with self.assertRaisesRegex(ValueError, "changed during inspection"):
                _read(self.path)

    def test_pre_read_change_with_same_inode_is_rejected(self):
        self.path.write_text("pytest>=8\\n", encoding="utf-8")
        original_open = os.open

        def rewrite_before_open(path, flags):
            previous = self.path.stat()
            self.path.write_text("pytest>=9\\n", encoding="utf-8")
            os.utime(self.path, ns=(previous.st_atime_ns, previous.st_mtime_ns + 2_000_000_000))
            return original_open(path, flags)

        with patch("devpilot.deps.os.open", side_effect=rewrite_before_open):
            with self.assertRaisesRegex(ValueError, "changed during inspection"):
                _read(self.path)


if __name__ == "__main__":
    unittest.main()
