"""Socket errors must not leak exception text through TCP probe reports."""

import errno
import json
import unittest
from unittest.mock import patch

from devpilot.core import tcp_check


class TCPErrorPrivacyTests(unittest.TestCase):
    def test_os_error_reports_errno_not_private_message(self):
        secret = 'private /home/user/.ssh/id_ed25519 token=abcd'
        with patch('devpilot.core.socket.create_connection',
                   side_effect=OSError(errno.EHOSTUNREACH, secret)) as connect:
            result = tcp_check('example.org', 443, 1.0)
        connect.assert_called_once_with(('example.org', 443), timeout=1.0)
        self.assertFalse(result['reachable'])
        self.assertEqual(result['error'], 'EHOSTUNREACH')
        self.assertNotIn(secret, json.dumps(result))

    def test_timeout_has_tcp_specific_classification(self):
        with patch('devpilot.core.socket.create_connection',
                   side_effect=TimeoutError('private socket error')):
            result = tcp_check('example.org', 443, 1)
        self.assertEqual(result['error'], 'TCP connection timed out')
        self.assertNotIn('private socket error', str(result))

    def test_refused_and_unknown_errors_are_safe(self):
        for problem, expected in (
            (ConnectionRefusedError('private hostname'), 'connection refused'),
            (OSError('secret internal error'), 'network I/O error'),
        ):
            with self.subTest(expected=expected), patch(
                'devpilot.core.socket.create_connection', side_effect=problem
            ):
                result = tcp_check('example.org', 443, 1)
            self.assertEqual(result['error'], expected)
            self.assertNotIn('private', str(result))
            self.assertNotIn('secret', str(result))


if __name__ == '__main__':
    unittest.main()
