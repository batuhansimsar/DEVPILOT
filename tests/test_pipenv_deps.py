"""Lockfile dependency inventory is bounded, canonical, and privacy-conscious."""

import tempfile
import unittest
from pathlib import Path

from devpilot.deps import scan
from devpilot.pipenv_deps import parse_pipfile_lock


class PipenvLockTests(unittest.TestCase):
    def test_grouped_packages_canonicalized_and_redacted(self):
        source = '{"_meta":{"sources":[{"url":"https://user:secret@example.com"}]},"default":{"Requests":{"version":"==2.30", "index":"private"},"my_pkg":{"version":"==1"}},"develop":{"Py.Test":{"version":"==8"}}}'
        report = parse_pipfile_lock(source)
        self.assertEqual(report, {'default': ['my-pkg', 'requests'], 'develop': ['py-test']})
        self.assertNotIn('secret', str(report))
        self.assertNotIn('private', str(report))

    def test_rejects_malformed_groups(self):
        for source in ('[]', '{"default":[]}', '{"develop":{"requests":"==1"}}', '{"default":{"requests":NaN}}'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                parse_pipfile_lock(source)

    def test_empty_file_reports_no_deps(self):
        self.assertEqual(parse_pipfile_lock('{}'), {})

    def test_scan_includes_pipfile_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Pipfile.lock').write_text(
                '{"default":{"Requests":{"version":"==2.31.0"}},'
                '"develop":{"pytest":{"version":"==8.0.0"}}}', encoding='utf-8'
            )
            report = scan(root)
        self.assertEqual(report['warnings'], [])
        self.assertEqual(report['totals']['Python'], 2)
        self.assertEqual(report['manifests'][0]['groups'], {
            'default': ['requests'], 'develop': ['pytest'],
        })


if __name__ == '__main__':
    unittest.main()
