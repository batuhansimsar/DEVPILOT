"""Regression tests for opt-in GET health checks without redirects or body reads."""

import contextlib
import io
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from devpilot.cli import main
from devpilot.httpcheck import http_check


class _GetOnly(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(405)
        self.end_headers()

    def do_GET(self):
        if self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', 'http://example.org/never-follow')
        else:
            self.send_response(200)
            # No response body is sent, despite the declared size.
            self.send_header('Content-Length', '1048576')
        self.end_headers()

    def log_message(self, *args):
        pass


class HTTPMethodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), _GetOnly)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def url(self, suffix='/health'):
        return f'http://127.0.0.1:{self.server.server_port}{suffix}'

    def test_head_is_default_and_get_is_opt_in(self):
        head = http_check(self.url())
        self.assertEqual(head['method'], 'HEAD')
        self.assertEqual(head['status'], 405)
        self.assertFalse(head['healthy'])
        get = http_check(self.url('/health?secret=hidden'), method='GET')
        self.assertEqual(get['method'], 'GET')
        self.assertEqual(get['status'], 200)
        self.assertTrue(get['healthy'])
        self.assertNotIn('hidden', str(get))

    def test_get_does_not_follow_redirect(self):
        result = http_check(self.url('/redirect'), method='GET')
        self.assertEqual(result['status'], 302)
        self.assertFalse(result['healthy'])

    def test_custom_status_works_with_get(self):
        result = http_check(self.url('/redirect'), method='GET',
                            expected_statuses=frozenset({302}))
        self.assertEqual(result['status'], 302)
        self.assertTrue(result['healthy'])

    def test_unsupported_method_rejected(self):
        for method in ('POST', 'DELETE', 'get', ''):
            with self.subTest(method=method), self.assertRaises(ValueError):
                http_check(self.url(), method=method)

    def test_cli_get_json(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(['http', self.url(), '--method', 'GET', '--json'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())['method'], 'GET')

    def test_cli_rejects_post_before_network(self):
        with patch('devpilot.cli.http_check') as probe, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                main(['http', self.url(), '--method', 'POST'])
        self.assertEqual(error.exception.code, 2)
        probe.assert_not_called()


if __name__ == '__main__':
    unittest.main()
