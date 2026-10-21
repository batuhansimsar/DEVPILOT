"""Regression tests for IDNA name/target equivalence, including ASCII."""

import unittest

from devpilot.idna_canonical import ensure_unambiguous_idna_hostname


class IDNAASCIIConsistencyTests(unittest.TestCase):
    def test_ascii_names_match_case_insensitively(self):
        for host, encoded in (
            ('example.org', b'example.org'),
            ('ExAmPlE.OrG', b'example.org'),
            ('xn--bcher-kva.example', b'XN--BCHER-KVA.EXAMPLE'),
            ('localhost', b'LOCALHOST'),
            ('example.org.', b'example.org.'),
        ):
            with self.subTest(host=host):
                ensure_unambiguous_idna_hostname(host, encoded)

    def test_ascii_target_changes_are_rejected_without_leaking_host(self):
        for host, encoded in (
            ('safe.example', b'other.example'),
            ('safe.example', b'safe.example.'),
            ('safe.example.', b'safe.example'),
            ('xn--bcher-kva.example', b'bucher.example'),
            ('localhost', b'127.0.0.1'),
        ):
            with self.subTest(host=host, encoded=encoded):
                with self.assertRaisesRegex(ValueError, 'ambiguous IDNA') as captured:
                    ensure_unambiguous_idna_hostname(host, encoded)
                self.assertNotIn(host, str(captured.exception))
                self.assertNotIn(encoded.decode('ascii'), str(captured.exception))

    def test_invalid_arguments_fail_with_generic_error(self):
        for host, encoded in ((None, b'example.org'), ('example.org', None),
                              ('example.org', 'example.org'), (123, b'example.org')):
            with self.subTest(host=host, encoded=encoded):
                with self.assertRaisesRegex(ValueError, 'ambiguous IDNA'):
                    ensure_unambiguous_idna_hostname(host, encoded)

    def test_unicode_normalization_remains_supported(self):
        for hostname in ('bücher.example', 'BÜCHER.example', 'bu\u0308cher.example'):
            with self.subTest(hostname=hostname):
                ensure_unambiguous_idna_hostname(hostname, hostname.encode('idna'))

    def test_unicode_lossy_mapping_still_rejected(self):
        hostname = 'faß.de'
        with self.assertRaisesRegex(ValueError, 'ambiguous IDNA'):
            ensure_unambiguous_idna_hostname(hostname, hostname.encode('idna'))


if __name__ == '__main__':
    unittest.main()
