"""Both public DNS validation entry points enforce identical safety rules."""

import unittest

from devpilot.http_host_validation import validate_http_dns_labels
from devpilot.http_url_validation import validate_dns_hostname_labels


class DNSValidatorConsistencyTests(unittest.TestCase):
    def test_valid_hostnames_are_accepted_by_both_entry_points(self):
        names = (
            b'example.org', b'EXAMPLE.org.', b'127.0.0.1',
            b'a' * 63 + b'.' + b'b' * 63 + b'.' + b'c' * 63 + b'.' + b'd' * 61,
        )
        for name in names:
            with self.subTest(name=name):
                for validate in (validate_http_dns_labels, validate_dns_hostname_labels):
                    validate(name)

    def test_invalid_names_have_identical_privacy_safe_errors(self):
        names = (
            b'', b'.example.org', b'example..org', b'example.org..',
            b'a' * 64 + b'.org', b'-bad.example', b'bad-.example',
            b'bad_name.example', b'bad!name.example', b'bad\x00name.example',
            b'example.org\nPRIVATE_SECRET', b'x' * 254, b'x' * 255 + b'.',
            'example.org', None,
        )
        for name in names:
            with self.subTest(name=name):
                errors = []
                for validate in (validate_http_dns_labels, validate_dns_hostname_labels):
                    with self.assertRaises(ValueError) as error:
                        validate(name)
                    errors.append(str(error.exception))
                self.assertEqual(errors[0], errors[1])
                self.assertNotIn('PRIVATE_SECRET', errors[0])


if __name__ == '__main__':
    unittest.main()
