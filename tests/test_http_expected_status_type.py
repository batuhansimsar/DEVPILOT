import unittest
from unittest.mock import patch

from devpilot.httpcheck import http_check


class ExpectedStatusTypeTests(unittest.TestCase):
    def test_scalar_expected_status_rejected_without_network(self):
        for statuses in (401, True, object()):
            with self.subTest(statuses=statuses), patch('devpilot.httpcheck.build_opener') as opener:
                with self.assertRaisesRegex(ValueError, 'expected HTTP status codes'):
                    http_check('https://example.invalid/ready', expected_statuses=statuses)
                opener.assert_not_called()

    def test_iterable_expected_statuses_still_work(self):
        for statuses in (frozenset({204}), [204], (204,)):
            with self.subTest(statuses=statuses), patch('devpilot.httpcheck.build_opener') as opener:
                opener.return_value.open.return_value.__enter__.return_value.status = 204
                response = http_check('https://example.invalid/ready', expected_statuses=statuses)
                self.assertTrue(response['reachable'])
                self.assertTrue(response['healthy'])


if __name__ == '__main__':
    unittest.main()
