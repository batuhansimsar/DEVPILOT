"""TCP and TLS probes must not dial lossy IDNA aliases."""

import unittest
from unittest.mock import patch

from devpilot.core import tcp_check
from devpilot.tlscheck import tls_check


class IDNAProbeIntegrationTests(unittest.TestCase):
    def test_lossy_printable_unicode_hosts_fail_before_network(self):
        for host in ('faß.de', 'ｔest.example', 'name。example'):
            for probe, socket_target in (
                (tcp_check, 'devpilot.core.socket.create_connection'),
                (tls_check, 'devpilot.tlscheck.socket.create_connection'),
            ):
                with self.subTest(host=host, probe=probe.__name__), patch(socket_target) as connect:
                    with self.assertRaisesRegex(ValueError, 'ambiguous IDNA'):
                        probe(host, 443, 1)
                    connect.assert_not_called()

    def test_canonical_unicode_hostname_is_still_dialed_as_requested(self):
        for probe, socket_target in (
            (tcp_check, 'devpilot.core.socket.create_connection'),
            (tls_check, 'devpilot.tlscheck.socket.create_connection'),
        ):
            with self.subTest(probe=probe.__name__), patch(
                socket_target, side_effect=ConnectionRefusedError('closed')
            ) as connect:
                report = probe('bücher.example', 443, 1)
                self.assertFalse(report['reachable'])
                connect.assert_called_once_with(('bücher.example', 443), timeout=1)


if __name__ == '__main__':
    unittest.main()
