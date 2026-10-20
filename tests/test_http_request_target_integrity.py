"""Regression tests for HTTP probe request-target integrity."""

import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check


class HTTPRequestTargetIntegrityTests(unittest.TestCase):
    def test_encoded_path_and_query_preserve_reserved_characters(self):
        url = "https://example.org/caf%C3%A9/a;b?query=x%20y&tag=foo/bar"
        with patch("devpilot.httpcheck.build_opener") as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check(url)
            request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, url)
        self.assertTrue(result["healthy"])
        self.assertEqual(result["status"], 204)
        self.assertNotIn("query", result["url"])

    def test_raw_unicode_is_percent_encoded_before_network_access(self):
        with patch("devpilot.httpcheck.build_opener") as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check("http://example.org/café")
            request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, "http://example.org/caf%C3%A9")
        self.assertEqual(result["url"], "http://example.org/caf%C3%A9")
        self.assertTrue(result["healthy"])

    def test_credentials_are_rejected_before_network_access(self):
        with patch("devpilot.httpcheck.build_opener") as opener:
            with self.assertRaisesRegex(ValueError, "without credentials"):
                http_check("http://user:pass@example.org/ready")
            opener.assert_not_called()


if __name__ == "__main__":
    unittest.main()
