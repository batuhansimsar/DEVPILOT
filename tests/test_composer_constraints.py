"""Reject malformed Composer dependency constraints without disclosing values."""

import json
import unittest

from devpilot.composer_deps import parse_composer_dependencies


class ComposerConstraintValidationTests(unittest.TestCase):
    def test_rejects_non_string_constraints_in_each_group(self):
        for group in ('require', 'require-dev'):
            for value in (None, True, 123, ['private-token'], {'secret': 'private-token'}):
                with self.subTest(group=group, value=value):
                    with self.assertRaises(ValueError) as caught:
                        parse_composer_dependencies(json.dumps({group: {'vendor/pkg': value}}))
                    self.assertIn(group, str(caught.exception))
                    self.assertNotIn('private-token', str(caught.exception))

    def test_valid_version_constraints_are_not_reported(self):
        self.assertEqual(parse_composer_dependencies(json.dumps({
            'require': {'php': '^8.3', 'psr/log': '>=3'},
            'require-dev': {'phpunit/phpunit': '^11'},
        })), {
            'require': ['php', 'psr/log'],
            'require-dev': ['phpunit/phpunit'],
        })

    def test_existing_strict_json_validation_remains_enabled(self):
        for value in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'non-finite'):
                    parse_composer_dependencies('{"require":{"vendor/pkg":' + value + '}}')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            parse_composer_dependencies('{"require":{}, "require":{}}')


if __name__ == '__main__':
    unittest.main()
