"""Certificate renewal thresholds use one clock sample."""

import datetime
import unittest
from unittest.mock import MagicMock, patch

from devpilot.tlscheck import tls_check


class TLSClockConsistencyTests(unittest.TestCase):
    def test_expiry_threshold_uses_single_now_and_consistent_days(self):
        expiry = datetime.datetime(2030, 6, 1, 12, 0, tzinfo=datetime.timezone.utc)
        first = expiry - datetime.timedelta(days=30, seconds=1)
        second = expiry - datetime.timedelta(days=30) + datetime.timedelta(seconds=1)

        class MovingClock(datetime.datetime):
            calls = 0

            @classmethod
            def now(cls, tz=None):
                cls.calls += 1
                return first if cls.calls == 1 else second

        with patch('devpilot.tlscheck.socket.create_connection') as connect, \
             patch('devpilot.tlscheck.ssl.create_default_context') as make_context, \
             patch('devpilot.tlscheck.datetime.datetime', MovingClock):
            connect.return_value = MagicMock()
            secured = MagicMock()
            secured.__enter__.return_value = secured
            secured.getpeercert.return_value = {'notAfter': 'Jun  1 12:00:00 2030 GMT'}
            make_context.return_value.wrap_socket.return_value = secured
            result = tls_check('example.org', 443, 2)
        self.assertEqual(MovingClock.calls, 1)
        self.assertEqual(result['expires_in_days'], 30)
        self.assertFalse(result['expires_soon'])
        self.assertTrue(result['tls_valid'])


if __name__ == '__main__':
    unittest.main()
