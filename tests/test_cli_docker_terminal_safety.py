"""Docker CLI human-readable output must not emit terminal control sequences."""

import unittest

from devpilot.cli import _human


class DockerTerminalSafetyTests(unittest.TestCase):
    def test_container_fields_are_escaped(self):
        report = {
            'exit_code': 0,
            'containers': [{
                'Names': 'web\x1b[31m',
                'Status': 'Up\nspoofed',
                'Image': 'nginx\u202e:latest',
            }],
        }
        output = _human('docker', report)
        self.assertEqual(
            output, r'web\x1b[31m: Up\x0aspoofed (nginx\u202e:latest)'
        )
        self.assertNotIn('\x1b', output)
        self.assertNotIn('\u202e', output)
        self.assertNotIn('\n', output)

    def test_failure_diagnostics_are_escaped(self):
        report = {'exit_code': 1, 'stderr': 'failure\x1b[2J\n'}
        self.assertEqual(_human('docker', report), r'failure\x1b[2J\x0a')

    def test_normal_output_and_empty_list_are_unchanged(self):
        report = {
            'exit_code': 0,
            'containers': [{'Names': 'web', 'Status': 'Up', 'Image': 'nginx:1.27'}],
        }
        self.assertEqual(_human('docker', report), 'web: Up (nginx:1.27)')
        report['containers'] = []
        self.assertEqual(_human('docker', report), 'No running containers')


if __name__ == '__main__':
    unittest.main()
