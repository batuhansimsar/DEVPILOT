"""Invalid DNS names must be rejected before either TLS or TCP dials."""

import unittest
from unittest.mock import patch

from devpilot.core import tcp_check
from devpilot.tlscheck import _tls_dial_host, tls_check


class DNSLabelValidationTests(unittest.TestCase):
    def test_invalid_dns_labels_are_rejected_without_network(self):
        overlong = '.'.join(['x' * 63] * 4)  # 255 bytes, above DNS's 253-byte limit.
        invalid = (
            'example..org', '.example.org', 'example.org..', '.',
            '-private.example.org', 'private-.example.org', overlong,
        )
        for probe, socket_target in (
            (tls_check, 'devpilot.tlscheck.socket.create_connection'),
            (tcp_check, 'devpilot.core.socket.create_connection'),
        ):
            with patch(socket_target) as connect:
                for host in invalid:
                    with self.subTest(probe=probe.__name__, host=host[:35]):
                        with self.assertRaisesRegex(ValueError, 'invalid IDNA hostname') as raised:
                            probe(host, 443, 1)
                        self.assertNotIn(host, str(raised.exception))
                connect.assert_not_called()

    def test_valid_hostname_boundaries_and_root_dot_reach_socket(self):
        maximum = '.'.join(['x' * 63] * 3 + ['x' * 61])  # Exactly 253 bytes.
        for host in (maximum, 'example.org.', 'bücher.example', 'localhost'):
            self.assertEqual(_tls_dial_host(host), host)
            for probe, socket_target in (
                (tls_check, 'devpilot.tlscheck.socket.create_connection'),
                (tcp_check, 'devpilot.core.socket.create_connection'),
            ):
                with self.subTest(probe=probe.__name__, host=host[:35]), patch(
                    socket_target, side_effect=ConnectionRefusedError('closed')
                ) as connect:
                    result = probe(host, 443, 1)
                    self.assertFalse(result['reachable'])
                    connect.assert_called_once_with((host, 443), timeout=1)


if __name__ == '__main__':
    unittest.main()
