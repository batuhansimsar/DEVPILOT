"""A broken docker ps record must not become an apparently complete inventory."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from devpilot.core import docker_status


class DockerOutputValidationTests(unittest.TestCase):
    def inspect(self, stdout):
        result = {
            'exit_code': 0, 'stdout': stdout, 'stdout_truncated': False,
            'stderr': '', 'stderr_truncated': False,
        }
        with patch('devpilot.core.command_result', return_value=result):
            return docker_status(Path('.'))

    def test_valid_multi_container_output(self):
        output = '\n'.join(
            json.dumps({'Names': name, 'Image': 'nginx', 'Status': 'Up'})
            for name in ('web', 'api')
        )
        report = self.inspect(output)
        self.assertEqual(report['exit_code'], 0)
        self.assertEqual([item['Names'] for item in report['containers']], ['web', 'api'])

    def test_json_scalar_or_array_cannot_pass_as_empty_inventory(self):
        for output in ('null\n', '[]\n', 'true\n', '"unexpected"\n', '42\n'):
            with self.subTest(output=output):
                report = self.inspect(output)
                self.assertEqual(report['exit_code'], 1)
                self.assertEqual(report['containers'], [])
                self.assertIn('unexpected response', report['error'])

    def test_malformed_line_discards_prior_valid_containers(self):
        report = self.inspect('{"Names":"web"}\nnot-json\n')
        self.assertEqual(report['exit_code'], 1)
        self.assertEqual(report['containers'], [])

    def test_empty_docker_output_is_valid(self):
        report = self.inspect('')
        self.assertEqual(report['exit_code'], 0)
        self.assertEqual(report['containers'], [])


if __name__ == '__main__':
    unittest.main()
