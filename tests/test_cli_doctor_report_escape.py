"""Doctor human-readable report must escape untrusted metadata consistently."""

import unittest

from devpilot.cli import _human


class DoctorOutputSafety(unittest.TestCase):
    def base(self):
        return {'path': '/repo', 'project_types': ['Python'], 'tools': [], 'warnings': [], 'ok': True}

    def test_environment_statuses_escape_control_characters(self):
        unsafe = '.env\x1b[2J\u202e'
        cases = [
            {'status': 'matched', 'template': unsafe},
            {'status': 'missing_keys', 'template': unsafe,
             'missing_keys': ['SAFE', 'BAD\n\x1b[31m\u202e']},
            {'status': 'local_absent', 'template': unsafe, 'expected_count': 2},
            {'status': 'unreadable_template', 'template': unsafe, 'detail': 'oops\r\x1b[0m'},
            {'status': 'unreadable_local', 'template': unsafe, 'detail': 'oops\r\x1b[0m'},
        ]
        for env in cases:
            with self.subTest(status=env['status']):
                report = self.base()
                report['environment'] = env
                result = _human('doctor', report)
                self.assertIn(r'.env\x1b[2J\u202e', result)
                self.assertNotIn('\x1b', result)
                self.assertNotIn('\u202e', result)
                self.assertNotIn('\r', result)
                self.assertEqual(result.count('\n'), 3)
                if env['status'] == 'missing_keys':
                    self.assertIn(r'BAD\x0a\x1b[31m\u202e', result)
                elif env['status'].startswith('unreadable'):
                    self.assertIn(r'oops\x0d\x1b[0m', result)

    def test_report_labels_cannot_inject_terminal_controls(self):
        report = self.base()
        report['project_types'] = ['Python\x1b[2J']
        report['tools'] = [{'name': 'tool\n\u202e', 'required_by': ['Test\r\x1b[31m'], 'available': True}]
        output = _human('doctor', report)
        self.assertIn(r'Python\x1b[2J', output)
        self.assertIn(r'tool\x0a\u202e', output)
        self.assertIn(r'Test\x0d\x1b[31m', output)
        self.assertNotIn('\x1b', output)
        self.assertNotIn('\u202e', output)
        self.assertEqual(output.count('\n'), 3)

    def test_normal_report_format_unchanged(self):
        report = self.base()
        report['tools'] = [{'name': 'Python', 'available': True, 'required_by': ['Python']}]
        report['environment'] = {'status': 'missing_keys', 'template': '.env.example', 'missing_keys': ['KEY']}
        self.assertEqual(_human('doctor', report), '\n'.join([
            'Project: /repo', 'Detected: Python', '  OK Python (for Python)',
            '  Environment: .env.example keys absent in .env: KEY (may be supplied externally)',
            'Doctor: healthy',
        ]))


if __name__ == '__main__':
    unittest.main()
