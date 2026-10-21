"""CLI argument validation must not emit control characters from paths."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path


class InvalidPathTerminalSafetyTests(unittest.TestCase):
    def test_missing_directory_path_cannot_inject_terminal_output(self):
        from devpilot.cli import main

        with tempfile.TemporaryDirectory() as directory:
            missing = str(Path(directory) / 'missing\x1b[31m\n\u202e')
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as error:
                main(['doctor', '--path', missing])

        self.assertEqual(error.exception.code, 2)
        output = stderr.getvalue()
        self.assertIn('Not a directory:', output)
        self.assertIn(r'missing\x1b[31m\x0a\u202e', output)
        self.assertNotIn('\x1b', output)
        self.assertNotIn('\u202e', output)
        self.assertNotIn('missing\n', output)


if __name__ == '__main__':
    unittest.main()
