import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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

    def test_redirect_not_followed(self):
        result = http_check(self.url('/redirect'))
        self.assertEqual(result['status'], 302)

    def test_invalid_urls_rejected(self):
        for value in ('file:///etc/passwd', 'http://user:pass@example.org/', 'http://', 'http://example.org:99999'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                http_check(value)


if __name__ == '__main__':
    unittest.main()
