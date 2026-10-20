"""HTTP health checks must support non-ASCII URL paths and queries."""

import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from devpilot.httpcheck import http_check


class _Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        # Require UTF-8 percent-encoding while preserving the original %2F.
        self.send_response(204 if self.path == '/caf%C3%A9?q=ni%C3%B1o&encoded=%2F' else 404)
        self.end_headers()

    def log_message(self, *args):
        pass


class UnicodeURLTests(unittest.TestCase):
    def test_utf8_path_query_and_existing_escape(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f'http://127.0.0.1:{server.server_port}/café?q=niño&encoded=%2F'
            result = http_check(url)
            self.assertTrue(result['healthy'], result)
            self.assertEqual(result['status'], 204)
            self.assertNotIn('q=niño', result['url'])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
