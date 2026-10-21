"""Direct DNS label validation must enforce type and total-name limits."""

import unittest

from devpilot.http_url_validation import validate_dns_hostname_labels


class HTTPDNSHelperBoundaryTests(unittest.TestCase):
    def test_accepts_complete_dns_name_at_maximum_length(self):
        hostname = b'.'.join((b'a' * 63, b'b' * 63, b'c' * 63, b'd' * 61))
        self.assertEqual(len(hostname), 253)
        for name in (hostname, hostname + b'.'):
            with self.subTest(trailing_root_dot=name.endswith(b'.')):
                validate_dns_hostname_labels(name)

    def test_rejects_complete_name_over_limit_without_exposing_input(self):
        hostname = b'.'.join((b'a' * 63,) * 4)
        self.assertEqual(len(hostname), 255)
        for name in (hostname, hostname + b'.'):
            with self.subTest(trailing_root_dot=name.endswith(b'.')):
                with self.assertRaisesRegex(ValueError, 'hostname length limit') as error:
                    validate_dns_hostname_labels(name)
                self.assertNotIn(name.decode(), str(error.exception))

    def test_rejects_wrong_types_with_sanitized_error(self):
        for value in (None, 'secret.internal', bytearray(b'secret.internal'), 123):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaisesRegex(ValueError, 'invalid DNS label') as error:
                    validate_dns_hostname_labels(value)
                self.assertNotIn('secret.internal', str(error.exception))

    def test_invalid_labels_and_empty_names_still_rejected(self):
        for name in (b'', b'.', b'api..example.com', b'-api.example.com', b'api_.example.com'):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, 'invalid DNS label'):
                    validate_dns_hostname_labels(name)


if __name__ == '__main__':
    unittest.main()
