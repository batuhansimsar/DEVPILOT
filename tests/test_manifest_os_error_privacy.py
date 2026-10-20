"""OS errors in manifest inspection must never expose local paths or secrets."""

import errno
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.manifest import read_package_json


class ManifestOSErrorPrivacyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'package.json').write_text('{"name":"demo"}', encoding='utf-8')

    def test_lstat_errors_report_only_standard_errno(self):
        sensitive = OSError(errno.EACCES, 'credential=TOPSECRET\x1b[31m\n',
                            '/private/credential=TOPSECRET')
        with patch('devpilot.manifest.Path.lstat', side_effect=sensitive):
            self.assertEqual(read_package_json(self.root),
                             (None, 'Cannot inspect package.json: EACCES'))

    def test_open_errors_do_not_expose_paths_or_raw_strerror(self):
        sensitive = OSError(errno.EIO, 'credential=TOPSECRET\x1b[31m\n',
                            '/private/credential=TOPSECRET')
        with patch('devpilot.manifest.os.open', side_effect=sensitive):
            self.assertEqual(read_package_json(self.root),
                             (None, 'Invalid package.json: EIO'))

    def test_errors_without_errno_use_generic_fallback(self):
        with patch('devpilot.manifest.os.open', side_effect=OSError('TOPSECRET\x1b[31m')):
            self.assertEqual(read_package_json(self.root),
                             (None, 'Invalid package.json: I/O error'))

    def test_regular_manifest_is_still_read(self):
        self.assertEqual(read_package_json(self.root), ({'name': 'demo'}, None))


if __name__ == '__main__':
    unittest.main()
