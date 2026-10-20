"""Fail-closed Git index boundary tests for the standalone secret audit."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.secret_audit import audit


class GitIndexIntegrityTests(unittest.TestCase):
    def test_unterminated_or_empty_records_are_not_treated_as_clean(self):
        malformed_listings = (
            b'credentials.json',
            b'src/main.py\0credentials.json',
            b'\0',
            b'src/main.py\0\0',
        )
        with tempfile.TemporaryDirectory() as directory:
            for listing in malformed_listings:
                with self.subTest(listing=listing), \
                     patch('devpilot.secret_audit.shutil.which', return_value='/usr/bin/git'), \
                     patch('devpilot.secret_audit._tracked_paths', return_value=listing):
                    with self.assertRaisesRegex(RuntimeError, 'Malformed Git index output'):
                        audit(Path(directory))

    def test_complete_and_empty_listings_still_work(self):
        with tempfile.TemporaryDirectory() as directory:
            for listing, count, findings in (
                (b'', 0, []),
                (b'src/main.py\0.env\0', 2, ['.env']),
            ):
                with self.subTest(listing=listing), \
                     patch('devpilot.secret_audit.shutil.which', return_value='/usr/bin/git'), \
                     patch('devpilot.secret_audit._tracked_paths', return_value=listing):
                    report = audit(Path(directory))
                    self.assertEqual(report['tracked_files_checked'], count)
                    self.assertEqual([item['path'] for item in report['findings']], findings)
                    self.assertEqual(report['ok'], not findings)


if __name__ == '__main__':
    unittest.main()
