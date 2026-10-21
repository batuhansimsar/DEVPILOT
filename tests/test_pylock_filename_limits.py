"""Guard direct pylock filename checks against oversized, impossible names."""

import unittest
from unittest.mock import patch

from devpilot.pylock import MAX_PYLOCK_FILENAME_CHARS, is_pylock_manifest


class PylockFilenameLimitsTests(unittest.TestCase):
    def test_filename_limit_boundary(self):
        prefix = 'pylock.'
        suffix = '.toml'
        variant = 'a' * (MAX_PYLOCK_FILENAME_CHARS - len(prefix + suffix))
        self.assertTrue(is_pylock_manifest(prefix + variant + suffix))
        self.assertFalse(is_pylock_manifest(prefix + variant + 'a' + suffix))

    def test_large_string_rejected_before_regex(self):
        class UnexpectedMatcher:
            def fullmatch(self, filename):
                raise AssertionError('should reject oversized names before matching')

        with patch('devpilot.pylock._PYLOCK_FILE', UnexpectedMatcher()):
            self.assertFalse(is_pylock_manifest('pylock.' + 'a' * 1_000_000 + '.toml'))

    def test_standard_manifest_still_recognized(self):
        self.assertTrue(is_pylock_manifest('pylock.toml'))
        self.assertTrue(is_pylock_manifest('pylock.dev.toml'))


if __name__ == '__main__':
    unittest.main()
