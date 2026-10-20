"""Duplicate JSON keys must not silently change the Node dependency inventory."""

import tempfile
import unittest
from pathlib import Path

from devpilot.deps import _parse, scan


class DuplicateNodeDependenciesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / 'package.json'

    def test_duplicate_root_dependency_group_is_rejected(self):
        self.manifest.write_text(
            '{"dependencies":{"safe":"1"},"dependencies":{"untrusted":"2"}}',
            encoding='utf-8',
        )
        report = scan(self.root)
        self.assertEqual(report['manifests'], [])
        self.assertEqual(len(report['warnings']), 1)
        self.assertIn('duplicate JSON object keys', report['warnings'][0])

    def test_duplicate_nested_dependency_name_is_rejected_without_echo(self):
        self.manifest.write_text(
            '{"dependencies":{"hidden-private-package":"1","hidden-private-package":"2"}}',
            encoding='utf-8',
        )
        report = scan(self.root)
        self.assertEqual(report['manifests'], [])
        self.assertNotIn('hidden-private-package', str(report))
        self.assertIn('duplicate JSON object keys', report['warnings'][0])

    def test_identical_names_in_distinct_groups_are_valid(self):
        self.manifest.write_text(
            '{"dependencies":{"demo":"1"},"devDependencies":{"demo":"2"}}',
            encoding='utf-8',
        )
        ecosystem, groups = _parse(self.manifest)
        self.assertEqual(ecosystem, 'Node.js')
        self.assertEqual(groups, {'dependencies': ['demo'], 'devDependencies': ['demo']})


if __name__ == '__main__':
    unittest.main()
