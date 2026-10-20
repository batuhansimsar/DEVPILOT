"""Reject overflowing JSON exponents anywhere in Composer manifests."""

import unittest

from devpilot.composer_deps import parse_composer_dependencies


class ComposerNonfiniteExponentTests(unittest.TestCase):
    def test_overflow_in_metadata_and_dependency_values_is_rejected(self):
        contents = (
            '{"extra":{"private-token":1e999},"require":{"php":"^8"}}',
            '{"require":{"php":-1E999}}',
            '{"require-dev":{"vendor/private":1.25e999}}',
        )
        for content in contents:
            with self.subTest(content=content):
                with self.assertRaisesRegex(ValueError, 'non-finite JSON number') as caught:
                    parse_composer_dependencies(content)
                self.assertNotIn('private-token', str(caught.exception))
                self.assertNotIn('vendor/private', str(caught.exception))

    def test_finite_exponents_do_not_break_valid_manifests(self):
        self.assertEqual(
            parse_composer_dependencies(
                '{"extra":{"value":1e2,"small":-1.25e-2},"require":{"php":"^8"}}'
            ),
            {'require': ['php']},
        )


if __name__ == '__main__':
    unittest.main()
