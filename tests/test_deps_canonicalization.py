"""PEP 503 dependency naming regression coverage."""

import tempfile
import unittest
from pathlib import Path

from devpilot.deps import scan


class CanonicalRequirementsTests(unittest.TestCase):
    def test_requirement_aliases_are_one_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'requirements.txt').write_text(
                'My_Pkg>=1\nmy.pkg[extra]==2\nMY--PKG~=3\nmy-pkg\n',
                encoding='utf-8',
            )
            report = scan(root)
        self.assertEqual(report['totals']['Python'], 1)
        self.assertEqual(report['manifests'][0]['groups']['requirements'], ['my-pkg'])

    def test_distinct_packages_remain_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'requirements.txt').write_text(
                'Requests>=2\nFlask==3\n--index-url https://example.org/simple\n',
                encoding='utf-8',
            )
            report = scan(root)
        self.assertEqual(report['totals']['Python'], 2)
        self.assertEqual(report['manifests'][0]['groups']['requirements'], ['flask', 'requests'])


if __name__ == '__main__':
    unittest.main()
