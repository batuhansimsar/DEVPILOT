"""Reject ambiguous or nonstandard Composer JSON without exposing private data."""

import json
import unittest

from devpilot.composer_deps import parse_composer_dependencies


class ComposerStrictJSONTests(unittest.TestCase):
    def test_duplicate_dependency_is_rejected_without_leaking_values(self):
        with self.assertRaisesRegex(ValueError, 'duplicate object keys') as caught:
            parse_composer_dependencies(
                '{"require":{"vendor/private":"https://user:secret@example.com",'
                '"vendor/private":"^2"}}'
            )
        self.assertNotIn('secret', str(caught.exception))
        self.assertNotIn('vendor/private', str(caught.exception))

    def test_duplicate_top_level_group_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate object keys'):
            parse_composer_dependencies('{"require":{"php":"^8"},"require":{"php":"^7"}}')

    def test_duplicate_nested_metadata_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate object keys'):
            parse_composer_dependencies('{"extra":{"token":"private","token":"other"}}')

    def test_nonfinite_numeric_literals_are_rejected(self):
        for constant in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(constant=constant):
                with self.assertRaisesRegex(ValueError, 'non-finite JSON number'):
                    parse_composer_dependencies('{"require":{"php":' + constant + '}}')

    def test_overflowing_json_exponents_are_rejected_without_leaking_metadata(self):
        for value in ('1e9999', '-1E9999', '9.9e9999'):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'non-finite JSON number') as caught:
                    parse_composer_dependencies(
                        '{"extra":{"secret-token":"do-not-log","estimate":' + value + '},'
                        '"require":{"php":"^8.3"}}'
                    )
                self.assertNotIn('do-not-log', str(caught.exception))
                self.assertNotIn('secret-token', str(caught.exception))

    def test_finite_metadata_floats_do_not_change_inventory(self):
        content = '{"extra":{"estimate":1.25e2},"require":{"php":"^8.3"}}'
        self.assertEqual(parse_composer_dependencies(content), {'require': ['php']})

    def test_valid_nested_config_remains_supported(self):
        content = json.dumps({'extra': {'branch-alias': {'dev-main': '1.x-dev'}},
                              'require': {'symfony/console': '^7', 'php': '^8.2'}})
        self.assertEqual(parse_composer_dependencies(content),
                         {'require': ['php', 'symfony/console']})


if __name__ == '__main__':
    unittest.main()
