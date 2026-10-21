import sys
import time
import tempfile
import unittest
from pathlib import Path

from devpilot.bounded_process import MAX_OUTPUT_BYTES, run_bounded


class BoundedProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def call_python(self, code, timeout=5):
        return run_bounded([sys.executable, '-c', code], self.root, timeout)

    def test_capture_stdout_and_stderr(self):
        result = self.call_python("import sys; print('hello'); print('oops', file=sys.stderr)")
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(result['stdout'], 'hello\n')
        self.assertEqual(result['stderr'], 'oops\n')
        self.assertFalse(result['stdout_truncated'])
        self.assertFalse(result['stderr_truncated'])

    def test_large_output_is_capped_without_deadlock(self):
        result = self.call_python(
            "import os; os.write(1, b'a'*2000000 + b'OUT-END'); "
            "os.write(2, b'b'*2000000 + b'ERR-END')"
        )
        self.assertEqual(result['exit_code'], 0)
        self.assertLessEqual(len(result['stdout'].encode()), MAX_OUTPUT_BYTES)
        self.assertLessEqual(len(result['stderr'].encode()), MAX_OUTPUT_BYTES)
        self.assertTrue(result['stdout'].endswith('OUT-END'))
        self.assertTrue(result['stderr'].endswith('ERR-END'))
        self.assertTrue(result['stdout_truncated'])
        self.assertTrue(result['stderr_truncated'])

    def test_invalid_utf8_cannot_expand_past_output_byte_limit(self):
        # Each invalid byte decodes to U+FFFD (three UTF-8 bytes). Both
        # reported streams must still respect MAX_OUTPUT_BYTES after decoding.
        result = self.call_python(
            "import os; os.write(1, b'\\xff'*20000 + b'OUT-END'); "
            "os.write(2, b'\\xfe'*20000 + b'ERR-END')"
        )
        self.assertEqual(result['exit_code'], 0)
        for stream, suffix in (('stdout', 'OUT-END'), ('stderr', 'ERR-END')):
            with self.subTest(stream=stream):
                self.assertLessEqual(len(result[stream].encode('utf-8')), MAX_OUTPUT_BYTES)
                self.assertTrue(result[stream].endswith(suffix))
                self.assertTrue(result[stream + '_truncated'])

    def test_invalid_utf8_short_output_still_uses_replacement_character(self):
        result = self.call_python("import os; os.write(1, b'\\xff' * 2)")
        self.assertEqual(result['stdout'], '\ufffd' * 2)
        self.assertFalse(result['stdout_truncated'])

    def test_nonzero_exit_preserved(self):
        result = self.call_python('import sys; sys.exit(7)')
        self.assertEqual(result['exit_code'], 7)

    def test_timeout_kills_child(self):
        result = self.call_python('import time; time.sleep(10)', timeout=0.05)
        self.assertIsNone(result['exit_code'])
        self.assertIn('Timed out', result['error'])

    def test_inherited_pipe_does_not_block_completion(self):
        # A grandchild inherits stdout/stderr after its parent exits.
        start = time.monotonic()
        result = self.call_python(
            "import subprocess, sys; "
            "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(3)']); "
            "print('parent done')", timeout=1,
        )
        self.assertEqual(result['exit_code'], 0)
        self.assertIn('parent done', result['stdout'])
        self.assertLess(time.monotonic() - start, 2.5)

    def test_missing_executable_is_reported(self):
        result = run_bounded(['devpilot-missing-executable-123456'], self.root)
        self.assertIsNone(result['exit_code'])
        self.assertIn('error', result)

    def test_working_directory_is_used(self):
        result = self.call_python('import os; print(os.getcwd())')
        self.assertEqual(Path(result['stdout'].strip()).resolve(), self.root.resolve())

    def test_invalid_utf8_replaced(self):
        result = self.call_python("import os; os.write(1, b'\\xff')")
        self.assertEqual(result['stdout'], '\ufffd')


if __name__ == '__main__':
    unittest.main()
