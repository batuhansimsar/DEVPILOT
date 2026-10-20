"""Non-UTF-8 dependency manifests must not disclose source bytes in warnings."""

import tempfile
import unittest
from pathlib import Path

from devpilot.deps import scan


class DependencyUnicodeErrorPrivacyTests(unittest.TestCase):
    def test_invalid_utf8_is_redacted_in_warnings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'requirements.txt').write_bytes(b'requests\nSECRET_PREFIX\xff\n')
            report = scan(root)
        self.assertEqual(report['manifests'], [])
        self.assertEqual(report['warnings'], [
            'requirements.txt: manifest is not valid UTF-8',
        ])
        self.assertNotIn('SECRET_PREFIX', str(report))

    def test_normal_utf8_requirements_are_still_counted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'requirements.txt').write_text('rèquests>=2\npytest>=8\n', encoding='utf-8')
            report = scan(root)
        self.assertEqual(report['warnings'], [])
        self.assertEqual(report['totals'], {'Python': 1})
        self.assertEqual(report['manifests'][0]['groups']['requirements'], ['pytest'])


if __name__ == '__main__':
    unittest.main()
