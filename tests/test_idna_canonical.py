"""Unicode network targets must not be redirected by lossy IDNA mapping."""

import unittest

from devpilot.idna_canonical import ensure_unambiguous_idna_hostname


class IDNACanonicalTests(unittest.TestCase):
    def test_printable_hosts_that_map_to_other_names_are_rejected(self):
        for host in ('faß.de', 'ｔest.example', 'name。example'):
            with self.subTest(host=host), self.assertRaisesRegex(ValueError, 'ambiguous IDNA') as caught:
                ensure_unambiguous_idna_hostname(host, host.encode('idna'))
            self.assertNotIn(host, str(caught.exception))

    def test_canonical_unicode_hosts_and_ascii_punycode_are_accepted(self):
        for host in ('bücher.example', 'BÜCHER.example', 'bu\u0308cher.example',
                     'xn--bcher-kva.example', 'example.org'):
            with self.subTest(host=host):
                ensure_unambiguous_idna_hostname(host, host.encode('idna'))

    def test_invalid_idna_decoding_does_not_leak_host_or_codec_error(self):
        with self.assertRaisesRegex(ValueError, 'ambiguous IDNA') as caught:
            ensure_unambiguous_idna_hostname('secret.é', b'xn--invalid-punycode-')
        self.assertNotIn('secret', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
