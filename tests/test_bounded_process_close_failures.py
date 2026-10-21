"""Report failed stream closures instead of crashing a reader thread."""

import unittest
from unittest.mock import Mock, patch

from devpilot.bounded_process import _capture_tail


class StreamCloseFailureTests(unittest.TestCase):
    def test_close_oserror_marks_capture_failed(self):
        stream = Mock()
        stream.fileno.return_value = 10
        stream.close.side_effect = OSError('sensitive file path')
        data = bytearray()
        totals, failed = [0], [False]
        with patch('devpilot.bounded_process.os.read', side_effect=[b'output', b'']):
            _capture_tail(stream, data, totals, failed)
        self.assertEqual(data, b'output')
        self.assertEqual(totals, [6])
        self.assertTrue(failed[0])
        stream.close.assert_called_once()

    def test_close_valueerror_marks_capture_failed(self):
        stream = Mock()
        stream.fileno.return_value = 10
        stream.close.side_effect = ValueError('closed')
        failed = [False]
        with patch('devpilot.bounded_process.os.read', return_value=b''):
            _capture_tail(stream, bytearray(), [0], failed)
        self.assertTrue(failed[0])

    def test_successful_close_preserves_success(self):
        stream = Mock()
        stream.fileno.return_value = 10
        failed = [False]
        with patch('devpilot.bounded_process.os.read', return_value=b''):
            _capture_tail(stream, bytearray(), [0], failed)
        self.assertFalse(failed[0])


if __name__ == '__main__':
    unittest.main()
