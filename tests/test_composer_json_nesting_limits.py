"""Deeply nested, untrusted Composer JSON must fail with private errors."""

import unittest

from devpilot.composer_deps import parse_composer_dependencies
from devpilot.composer_lock import parse_composer_lock


class ComposerJSONNestingLimitsTests(unittest.TestCase):
    def test_direct_parsers_reject_extreme_nesting_without_traceback_or_secrets(self):
        # Less than 512 KiB but deep enough to exhaust the JSON parser stack.
        hostile_metadata = '[' * 12000 + '"private-token-do-not-log"' + ']' * 12000
        content = '{"extra":' + hostile_metadata + ',"require":{"php":"^8"}}'
        for parser, expected in (
            (parse_composer_dependencies, 'invalid composer.json JSON'),
            (parse_composer_lock, 'invalid composer.lock JSON'),
        ):
            with self.subTest(parser=parser.__name__):
                with self.assertRaisesRegex(ValueError, expected) as caught:
                    parser(content)
                self.assertNotIn('private-token', str(caught.exception))
                self.assertIsNone(caught.exception.__cause__)

    def test_normal_nested_metadata_remains_supported(self):
        content = '{"extra":{"nested":[{"ignored":1}]},"require":{"php":"^8"},"packages":[]}'
        self.assertEqual(parse_composer_dependencies(content), {'require': ['php']})
        self.assertEqual(parse_composer_lock(content), {})


if __name__ == '__main__':
    unittest.main()
