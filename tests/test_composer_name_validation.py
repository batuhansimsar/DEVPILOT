"""Composer package validation must never publish arbitrary manifest keys."""

import json
import unittest

from devpilot.composer_deps import parse_composer_dependencies


class ComposerPackageNameValidationTests(unittest.TestCase):
    def test_vendor_and_platform_dependencies_are_supported(self):
        payload = {
            'require': {
                'symfony/console': '^7', 'php': '^8.2', 'php-64bit': '*',
                'ext-json': '*', 'lib-icu': '*', 'composer-runtime-api': '^2',
                'HHVM': '*', 'vendor.with-dots/package_name': '1.0',
            },
            'require-dev': {'phpunit/phpunit': '^11', 'composer-plugin-api': '^2'},
        }
        result = parse_composer_dependencies(json.dumps(payload))
        self.assertEqual(result['require'], sorted(payload['require']))
        self.assertEqual(result['require-dev'], sorted(payload['require-dev']))

    def test_invalid_keys_cannot_be_echoed_in_errors(self):
        for key in (
            'https://user:secret@example.com/private',
            'PRIVATE_ACCESS_TOKEN',
            'vendor/package/other',
            'vendor/package\nSECRET=123',
            '@scope/npm-package',
            'bad package',
        ):
            with self.subTest(key=key):
                with self.assertRaises(ValueError) as caught:
                    parse_composer_dependencies(json.dumps({
                        'require': {'psr/log': '^3', key: '*'},
                    }))
                self.assertEqual(str(caught.exception),
                                 'composer.json require contains an invalid package name')
                self.assertNotIn(key, str(caught.exception))

    def test_invalid_development_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'require-dev contains an invalid package name'):
            parse_composer_dependencies(json.dumps({
                'require-dev': {'token:secret': '*'},
            }))


if __name__ == '__main__':
    unittest.main()
