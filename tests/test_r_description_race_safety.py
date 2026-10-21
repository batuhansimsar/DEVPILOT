"""R package DESCRIPTION verification must resist file replacement races."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.r_tests import _valid_package_description


class RDescriptionRaceSafetyTests(unittest.TestCase):
    def test_regular_package_is_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest = Path(folder) / 'DESCRIPTION'
            manifest.write_text('Package: stablepkg\nVersion: 1.0\n', encoding='utf-8')
            self.assertTrue(_valid_package_description(manifest))

    def test_symlink_swap_between_stat_and_open_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = root / 'DESCRIPTION'
            target = root / 'outside'
            manifest.write_text('Package: stablepkg\n', encoding='utf-8')
            target.write_text('Package: externalpkg\n', encoding='utf-8')
            try:
                probe = root / 'probe'
                probe.symlink_to(target)
                probe.unlink()
            except (OSError, NotImplementedError):
                self.skipTest('symlinks unavailable')
            original_open = os.open

            def replace_with_symlink(path, flags, *args, **kwargs):
                manifest.unlink()
                manifest.symlink_to(target)
                return original_open(path, flags, *args, **kwargs)

            with patch('devpilot.r_tests.os.open', side_effect=replace_with_symlink):
                self.assertFalse(_valid_package_description(manifest))

    def test_replacement_with_different_regular_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = root / 'DESCRIPTION'
            replacement = root / 'replacement'
            manifest.write_text('Package: original\n', encoding='utf-8')
            replacement.write_text('Package: injected\n', encoding='utf-8')
            original_open = os.open

            def swap(path, flags, *args, **kwargs):
                os.replace(replacement, manifest)
                return original_open(path, flags, *args, **kwargs)

            with patch('devpilot.r_tests.os.open', side_effect=swap):
                self.assertFalse(_valid_package_description(manifest))

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'requires POSIX FIFOs')
    def test_special_file_is_never_opened(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest = Path(folder) / 'DESCRIPTION'
            os.mkfifo(manifest)
            self.assertFalse(_valid_package_description(manifest))


if __name__ == '__main__':
    unittest.main()
