"""Ensure overlong DNS hostnames never reach the HTTP transport."""

import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check


class HTTPHostnameTotalLengthTests(unittest.TestCase):
    def test_hostname_at_dns_length_limit_is_accepted(self):
        hostname = '.'.join(('a' * 63, 'b' * 63, 'c' * 63, 'd' * 61))
        self.assertEqual(len(hostname), 253)
        for name in (hostname, hostname + '.'):
            with self.subTest(trailing_dot=name.endswith('.')):
                with patch('devpilot.httpcheck.build_opener') as opener:
                    opener.return_value.open.return_value.__enter__.return_value.status = 204
                    result = http_check(f'https://{name}/health')
                self.assertTrue(result['healthy'])
                opener.assert_called_once()

    def test_overlong_total_hostname_is_rejected_before_network(self):
        # Each 63-byte label is legal; the combined 255-byte name is not.
        hostname = '.'.join(('a' * 63,) * 4)
        self.assertEqual(len(hostname), 255)
        for name in (hostname, hostname + '.'):
            with self.subTest(trailing_dot=name.endswith('.')):
                with patch('devpilot.httpcheck.build_opener') as opener:
                    with self.assertRaisesRegex(ValueError, 'DNS hostname length limit') as caught:
                        http_check(f'https://{name}/health?token=never-expose')
                    self.assertNotIn('never-expose', str(caught.exception))
                    opener.assert_not_called()


if __name__ == '__main__':
    unittest.main()
