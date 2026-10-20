"""Invalid command arguments must not spawn a child or crash diagnostics."""

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from devpilot.bounded_process import run_bounded


class BoundedProcessArgumentsTests(unittest.TestCase):
    def test_rejects_invalid_argv_before_spawning(self):
        bad_commands = [[], [''], ['echo', 'bad\0arg'], [None], ['echo', 3], 'echo']
        with TemporaryDirectory() as temp:
            with patch('devpilot.bounded_process.subprocess.Popen') as popen:
                for argv in bad_commands:
                    with self.subTest(argv=argv):
                        result = run_bounded(argv, Path(temp))
                        self.assertIsNone(result['exit_code'])
                        self.assertIn('argv', result['error'])
                        self.assertEqual(result['argv'], argv)
                popen.assert_not_called()

    def test_valid_argv_still_executes(self):
        with TemporaryDirectory() as temp:
            result = run_bounded([sys.executable, '-c', 'print("ok")'], Path(temp))
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['stdout'], 'ok\n')
        self.assertNotIn('error', result)


if __name__ == '__main__':
    unittest.main()
