"""TCP probes must share the strict hostname rules used by TLS probes."""

import unittest
from unittest.mock import patch

from devpilot.core import tcp_check


class TCPHostValidationTests(unittest.TestCase):
    def test_ambiguous_hosts_are_rejected_without_network_access(self):
        invalid = (
            'https://example.org', 'example.org:443', 'example.org/path',
            'example.org?x=1', 'user@example.org', '[::1]:443',
            '[example.org]', '[127.0.0.1]', '::1]', '[::1',
            'example.org\u202e', 'example.org\u2066',
        )
        with patch('devpilot.core.socket.create_connection') as connect:
            for host in invalid:
                with self.subTest(host=host), self.assertRaises(ValueError):
                    tcp_check(host, 443, 1)
            connect.assert_not_called()

    def test_bracketed_ipv6_is_normalized_only_for_network_dial(self):
        with patch('devpilot.core.socket.create_connection') as connect:
            result = tcp_check('[::1]', 443, 1)
        connect.assert_called_once_with(('::1', 443), timeout=1)
        self.assertEqual(result['host'], '[::1]')
        self.assertTrue(result['reachable'])

    def test_plain_hostnames_and_ipv6_remain_valid(self):
        with patch('devpilot.core.socket.create_connection') as connect:
            for host in ('example.org', '127.0.0.1', '::1'):
                with self.subTest(host=host):
                    self.assertTrue(tcp_check(host, 443, 1)['reachable'])
        self.assertEqual([call.args[0][0] for call in connect.call_args_list],
                         ['example.org', '127.0.0.1', '::1'])


if __name__ == '__main__':
    unittest.main()
