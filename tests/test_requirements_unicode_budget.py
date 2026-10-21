"""Enforce a byte budget for direct pip requirements parser callers."""

import unittest

from devpilot.requirements_deps import (
    MAX_REQUIREMENTS_INPUT_CHARS,
    parse_requirements_dependencies,
)


class RequirementsUnicodeBudgetTests(unittest.TestCase):
    def test_multibyte_input_is_limited_by_encoded_bytes(self):
        secret = '🔑' * (MAX_REQUIREMENTS_INPUT_CHARS // 4 + 1)
        self.assertLess(len(secret), MAX_REQUIREMENTS_INPUT_CHARS)
        with self.assertRaisesRegex(ValueError, 'safe size limit') as caught:
            parse_requirements_dependencies(secret)
        self.assertNotIn(secret[:2], str(caught.exception))

    def test_lone_surrogate_is_rejected_without_leaking_content(self):
        with self.assertRaisesRegex(ValueError, 'valid Unicode') as caught:
            parse_requirements_dependencies('requests==2\n\ud800')
        self.assertNotIn('requests', str(caught.exception))

    def test_small_unicode_comment_does_not_change_dependency_names(self):
        self.assertEqual(parse_requirements_dependencies('requests==2\n# café\n'), ['requests'])

    def test_oversized_ascii_input_is_still_rejected(self):
        with self.assertRaisesRegex(ValueError, 'safe size limit'):
            parse_requirements_dependencies('x' * (MAX_REQUIREMENTS_INPUT_CHARS + 1))


if __name__ == '__main__':
    unittest.main()
