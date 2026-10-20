"""Regression tests for TLS input validation and safe CLI errors."""

import contextlib
import io
import unittest
from unittest.mock import patch

from devpilot.tlscheck import tls_check
from devpilot.cli import main


class TLSInputValidationTests(unittest.TestCase):
    def test_invalid_inputs_never_open_a_socket(self):
        with patch('devpilot.tlscheck.socket.create_connection') as connect:
            for host, port, timeout in (
                ('', 443, 3),
                ('bad host', 443, 3),
                ('example.org\nspoof', 443, 3),
                ('example.org', 0, 3),
                ('example.org', 65536, 3),
                ('example.org', 443, 0),
                ('example.org', 443, 31),
            ):
                with self.subTest(host=host, port=port, timeout=timeout):
                    with self.assertRaises(ValueError):
                        tls_check(host, port, timeout)
            connect.assert_not_called()

    def test_cli_invalid_tls_hostname_has_argument_error_not_traceback(self):
        with patch('devpilot.cli.tls_check', side_effect=ValueError('host must be a hostname')) as check:
            with contextlib.redirect_stderr(io.StringIO()) as err:
                with self.assertRaises(SystemExit) as raised:
                    main(['check', 'bad host', '443', '--tls'])
            self.assertEqual(raised.exception.code, 2)
            self.assertIn('host must be a hostname', err.getvalue())
            check.assert_called_once()


if __name__ == '__main__':
    unittest.main()
