"""ASCII IDNA targets must not differ from the hostname being reported."""

import unittest

from devpilot.idna_canonical import ensure_unambiguous_idna_hostname


class ASCIITargetConsistencyTests(unittest.TestCase):
    def test_mismatched_ascii_targets_fail_without_leaking_input(self):
        for host, encoded in (
            ('example.org', b'other.example'),
            ('xn--bcher-kva.example', b'other.example'),
            ('example.org', b'example.org.'),
            ('example.org', b'example.org\x00'),
            ('example.org', b'\xff.example.org'),
        ):
            with self.subTest(host=host, encoded=encoded):
                with self.assertRaisesRegex(
                    ValueError, '^host contains an ambiguous IDNA hostname$'
                ) as caught:
                    ensure_unambiguous_idna_hostname(host, encoded)
                self.assertNotIn(host, str(caught.exception))
                self.assertNotIn('other.example', str(caught.exception))

    def test_case_only_differences_remain_valid(self):
        for host, encoded in (
            ('EXAMPLE.ORG', b'example.org'),
            ('xn--bcher-kva.example', b'XN--BCHER-KVA.EXAMPLE'),
            ('example.org.', b'EXAMPLE.ORG.'),
        ):
            with self.subTest(host=host):
                ensure_unambiguous_idna_hostname(host, encoded)

    def test_invalid_argument_types_fail_closed(self):
        for host, encoded in (
            ('example.org', None),
            ('example.org', 'example.org'),
            (None, b'example.org'),
            (b'example.org', b'example.org'),
        ):
            with self.subTest(host=host, encoded=encoded):
                with self.assertRaisesRegex(ValueError, 'ambiguous IDNA'):
                    ensure_unambiguous_idna_hostname(host, encoded)


if __name__ == '__main__':
    unittest.main()
