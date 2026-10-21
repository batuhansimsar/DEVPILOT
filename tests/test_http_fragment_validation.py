"""Never report a successful HTTP check for a silently truncated URL."""

import unittest
from unittest.mock import patch

from devpilot.http_fragment import reject_http_fragment


class FragmentValidationTests(unittest.TestCase):
    def test_rejects_nonempty_and_empty_fragments_without_leaking_values(self):
        for url in (
            'https://example.org/health#',
            'https://example.org/health#private-token',
            'https://example.org/health?stage=ready#private-token',
        ):
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, 'fragments') as caught:
                reject_http_fragment(url)
            self.assertNotIn('private-token', str(caught.exception))

    def test_encoded_hash_is_not_a_fragment(self):
        for url in ('https://example.org/a%23b', 'https://example.org/?q=%23'):
            with self.subTest(url=url):
                reject_http_fragment(url)


class HTTPFragmentIntegrationTests(unittest.TestCase):
    def test_rejects_fragments_before_opening_transport(self):
        from devpilot.httpcheck import http_check

        for url in ('https://example.org/health#private-token',
                    'https://example.org/health#'):
            with self.subTest(url=url), patch('devpilot.httpcheck.build_opener') as opener:
                with self.assertRaisesRegex(ValueError, 'fragments') as raised:
                    http_check(url)
                self.assertNotIn('private-token', str(raised.exception))
                opener.assert_not_called()

    def test_percent_encoded_hash_is_sent_as_a_path_character(self):
        from devpilot.httpcheck import http_check

        with patch('devpilot.httpcheck.build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.status = 204
            result = http_check('https://example.org/a%23b')
            self.assertTrue(result['healthy'])
            request = opener.return_value.open.call_args.args[0]
            self.assertIn('/a%23b', request.full_url)


if __name__ == '__main__':
    unittest.main()
