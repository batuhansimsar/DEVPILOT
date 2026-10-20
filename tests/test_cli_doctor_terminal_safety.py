"""Doctor project path should be safe in human-readable terminal output."""

import unittest

from devpilot.cli import _human


class DoctorTerminalSafetyTests(unittest.TestCase):
    def test_doctor_path_is_escaped(self):
        report = {
            'path': '/repo\x1b[31m\n\u202e',
            'project_types': ['Python'],
            'tools': [],
            'warnings': [],
            'ok': True,
        }
        output = _human('doctor', report)
        self.assertNotIn('\x1b', output)
        self.assertNotIn('\u202e', output)
        self.assertIn(r'/repo\x1b[31m\x0a\u202e', output)
        self.assertEqual(output.count('\n'), 2)

    def test_regular_path_is_unchanged(self):
        report = {
            'path': '/repo',
            'project_types': [],
            'tools': [],
            'warnings': [],
            'ok': False,
        }
        self.assertIn('Project: /repo', _human('doctor', report))


if __name__ == '__main__':
    unittest.main()
