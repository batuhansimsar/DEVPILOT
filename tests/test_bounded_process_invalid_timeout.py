"""Invalid deadlines must never leave a spawned test command unmanaged."""

import sys
import tempfile
import unittest
from pathlib import Path

from devpilot.bounded_process import run_bounded


class InvalidTimeoutTests(unittest.TestCase):
    def test_invalid_timeout_never_starts_child(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            marker = root / 'launched'
            argv = [sys.executable, '-c',
                    "from pathlib import Path; Path('launched').write_text('yes')"]
            for timeout in (0, -1, float('nan'), float('inf'),
                            -float('inf'), None, '5', True, 10**1000):
                with self.subTest(timeout=repr(timeout)):
                    result = run_bounded(argv, root, timeout=timeout)
                    self.assertEqual(result['argv'], argv)
                    self.assertIsNone(result['exit_code'])
                    self.assertIn('positive finite', result['error'])
                    self.assertFalse(marker.exists(), 'invalid timeout spawned child')

    def test_valid_finite_timeout_executes(self):
        with tempfile.TemporaryDirectory() as folder:
            result = run_bounded(
                [sys.executable, '-c', "print('ready')"], Path(folder),
                timeout=2.0,
            )
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['stdout'], 'ready\n')


if __name__ == '__main__':
    unittest.main()
