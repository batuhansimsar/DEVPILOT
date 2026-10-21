"""Regression tests for explicit OPTIONS HTTP health probes."""

import contextlib
import io
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from devpilot.cli import main
from devpilot.httpcheck import http_check


class _OptionsHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(405)
        self.end_headers()

    def do_OPTIONS(self):
        if self.path.startswith('/redirect'):
            self.send_response(302)
            self.send_header('Location', 'http://example.org/do-not-follow')
        elif self.path.startswith('/forbidden'):
            self.send_response(403)
        else:
            self.send_response(204)
        self.end_headers()

    def log_message(self, *args):
        pass


class HTTPOptionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), _OptionsHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def url(self, path='/health'):
        return f'http://127.0.0.1:{self.server.server_port}{path}'

    def test_options_is_opt_in_and_reports_method(self):
        head = http_check(self.url())
        self.assertEqual(head['method'], 'HEAD')
        self.assertEqual(head['status'], 405)
        options = http_check(self.url('/health?token=do-not-print'), method='OPTIONS')
        self.assertEqual(options['method'], 'OPTIONS')
        self.assertEqual(options['status'], 204)
        self.assertTrue(options['healthy'])
        self.assertNotIn('do-not-print', str(options))

    def test_options_redirect_is_not_followed(self):
        result = http_check(self.url('/redirect'), method='OPTIONS')
        self.assertTrue(result['reachable'])
        self.assertEqual(result['status'], 302)
        self.assertFalse(result['healthy'])

    def test_options_accepts_explicit_expected_status(self):
        result = http_check(
            self.url('/forbidden'), method='OPTIONS',
            expected_statuses=frozenset({403}),
        )
        self.assertEqual(result['status'], 403)
        self.assertTrue(result['healthy'])

    def test_cli_options_json(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(['http', self.url(), '--method', 'OPTIONS', '--json'])
        self.assertEqual(exit_code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload['method'], 'OPTIONS')
        self.assertEqual(payload['status'], 204)

    def test_other_methods_remain_disallowed(self):
        for method in ('POST', 'PATCH', 'options', ''):
            with self.subTest(method=method), self.assertRaises(ValueError):
                http_check(self.url(), method=method)


if __name__ == '__main__':
    unittest.main()
