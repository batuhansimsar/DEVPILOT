import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import URLError

from devpilot.httpcheck import http_check


class _Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        if self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', 'http://example.org/never-follow')
        elif self.path == '/failure':
            self.send_response(503)
        else:
            self.send_response(204)
        self.end_headers()

    def log_message(self, *args):
        pass


class _UnwantedProxy(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(502)
        self.end_headers()

    def log_message(self, *args):
        pass


class HTTPCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), _Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def url(self, suffix=''):
        return f'http://127.0.0.1:{self.server.server_port}{suffix}'

    def test_success(self):
        result = http_check(self.url('/health?secret=dont-print'))
        self.assertTrue(result['healthy'])
        self.assertEqual(result['status'], 204)
        self.assertNotIn('secret', str(result))

    def test_server_error_is_unhealthy_but_reachable(self):
        result = http_check(self.url('/failure'))
        self.assertTrue(result['reachable'])
        self.assertFalse(result['healthy'])
        self.assertEqual(result['status'], 503)

    def test_redirect_not_followed_or_marked_healthy(self):
        result = http_check(self.url('/redirect'))
        self.assertTrue(result['reachable'])
        self.assertFalse(result['healthy'])
        self.assertEqual(result['status'], 302)

    def test_ipv6_report_uses_valid_bracketed_address(self):
        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check('http://[::1]:8080/ready?token=hidden')
        self.assertEqual(result['url'], 'http://[::1]:8080/ready')
        self.assertTrue(result['healthy'])

    def test_ignores_ambient_http_proxy(self):
        proxy = ThreadingHTTPServer(('127.0.0.1', 0), _UnwantedProxy)
        thread = threading.Thread(target=proxy.serve_forever, daemon=True)
        thread.start()
        try:
            proxy_url = f'http://127.0.0.1:{proxy.server_port}'
            with patch('urllib.request.getproxies', return_value={'http': proxy_url}), \
                 patch('urllib.request.proxy_bypass', return_value=False):
                result = http_check(self.url('/health'))
            self.assertEqual(result['status'], 204)
            self.assertTrue(result['healthy'])
        finally:
            proxy.shutdown()
            proxy.server_close()
            thread.join()

    def test_environment_proxy_does_not_intercept_direct_health_check(self):
        # A broken ambient proxy must not replace the endpoint being probed.
        proxy_settings = {
            'http_proxy': 'http://127.0.0.1:1',
            'HTTP_PROXY': 'http://127.0.0.1:1',
            'no_proxy': '',
            'NO_PROXY': '',
        }
        with patch.dict(os.environ, proxy_settings):
            result = http_check(self.url('/health'))
        self.assertTrue(result['reachable'], result)
        self.assertEqual(result['status'], 204)

    def test_network_failure_has_consistent_health_field(self):
        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.side_effect = URLError('unreachable')
            result = http_check(self.url('/health'))
        self.assertFalse(result['reachable'])
        self.assertFalse(result['healthy'])
        self.assertIsNone(result['status'])

    def test_invalid_urls_rejected(self):
        for value in (
            'file:///etc/passwd', 'http://user:pass@example.org/',
            'http://@example.org/', 'http://', 'http://example.org:99999',
            'http://example.org:', 'http://example.org:0', 'http://example.org/\npath',
            'http://example.org/\x1b[31m',
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                http_check(value)


if __name__ == '__main__':
    unittest.main()
