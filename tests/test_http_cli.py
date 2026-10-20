import contextlib
import io
import json
import unittest
from unittest.mock import patch

from devpilot.cli import main


class HTTPCLITests(unittest.TestCase):
    def call(self, args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(args)
        return exit_code, output.getvalue()

    def test_http_json_success(self):
        report = {'url': 'http://127.0.0.1:8080/health', 'reachable': True,
                  'status': 204, 'healthy': True, 'latency_ms': 1.0}
        with patch('devpilot.cli.http_check', return_value=report) as probe:
            code, output = self.call(['http', 'http://127.0.0.1:8080/health', '--json'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)['status'], 204)
        probe.assert_called_once_with('http://127.0.0.1:8080/health', 3.0)

    def test_http_unhealthy_returns_nonzero(self):
        report = {'url': 'http://127.0.0.1:8080/health', 'reachable': True,
                  'status': 503, 'healthy': False, 'latency_ms': 1.0}
        with patch('devpilot.cli.http_check', return_value=report):
            code, output = self.call(['http', 'http://127.0.0.1:8080/health'])
        self.assertEqual(code, 1)
        self.assertIn('HTTP 503', output)

    def test_http_bad_url_is_argument_error(self):
        with patch('devpilot.cli.http_check', side_effect=ValueError('invalid URL')):
            with self.assertRaises(SystemExit) as raised:
                self.call(['http', 'file:///etc/passwd'])
        self.assertEqual(raised.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
