"""Untrusted dependency group labels must not inject terminal controls."""

import unittest

from devpilot.cli import _human


class DependencyGroupTerminalSafetyTests(unittest.TestCase):
    def test_dependency_group_labels_are_escaped(self):
        report = {
            'root': '/repo',
            'manifests': [{
                'ecosystem': 'Node.js',
                'path': 'package.json',
                'count': 1,
                'groups': {'dependencies\x1b[31m\n\u202e': ['example']},
            }],
            'warnings': [],
        }
        output = _human('deps', report)
        self.assertNotIn('\x1b', output)
        self.assertNotIn('\u202e', output)
        self.assertEqual(output.count('\n'), 2)
        self.assertIn(r'dependencies\x1b[31m\x0a\u202e: example', output)

    def test_ordinary_dependency_groups_unchanged(self):
        report = {
            'root': '/repo',
            'manifests': [{
                'ecosystem': 'Python',
                'path': 'pyproject.toml',
                'count': 1,
                'groups': {'group:dev': ['pytest']},
            }],
            'warnings': [],
        }
        self.assertIn('    group:dev: pytest', _human('deps', report))


if __name__ == '__main__':
    unittest.main()
