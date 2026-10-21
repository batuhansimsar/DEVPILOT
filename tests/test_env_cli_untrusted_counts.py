"""Environment rendering must not trust caller-provided report counts."""

import unittest
from devpilot.env_cli import format_environment


class UntrustedEnvironmentCountTests(unittest.TestCase):
    def test_valid_counts_are_preserved(self):
        for status in ('matched', 'local_absent'):
            with self.subTest(status=status):
                rendered = format_environment({'status': status, 'template': '.env.example', 'expected_count': 3})
                self.assertIn('3 names', rendered)

    def test_untrusted_counts_cannot_inject_terminal_controls(self):
        for status in ('matched', 'local_absent'):
            for count in ('\x1b[2Jfake', '\nInjected: pass', -1, True, 1.5):
                with self.subTest(status=status, count=count):
                    rendered = format_environment({'status': status, 'template': '.env.example', 'expected_count': count})
                    self.assertIn('unknown names', rendered)
                    self.assertNotIn('\x1b', rendered)
                    self.assertNotIn('\n', rendered)
                    self.assertNotIn('Injected:', rendered)


if __name__ == '__main__':
    unittest.main()
