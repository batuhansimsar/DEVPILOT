"""Reject Composer case aliases that represent the same package."""

import json
import unittest

from devpilot.composer_deps import parse_composer_dependencies


class ComposerCaseAliasTests(unittest.TestCase):
    def test_vendor_package_case_aliases_rejected(self):
        for group in ('require', 'require-dev'):
            with self.subTest(group=group):
                with self.assertRaises(ValueError) as caught:
                    parse_composer_dependencies(json.dumps({group: {
                        'vendor/package': '^1', 'Vendor/Package': '^2',
                    }}))
                self.assertIn('duplicate case-insensitive package names', str(caught.exception))
                self.assertNotIn('vendor/package', str(caught.exception))

    def test_platform_requirement_case_aliases_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate case-insensitive package names'):
            parse_composer_dependencies(json.dumps({'require': {'HHVM': '*', 'hhvm': '^4'}}))

    def test_distinct_case_preserved_and_group_boundaries_independent(self):
        self.assertEqual(parse_composer_dependencies(json.dumps({
            'require': {'HHVM': '*', 'Vendor/Package': '^1'},
            'require-dev': {'vendor/package': '^2'},
        })), {
            'require': ['HHVM', 'Vendor/Package'],
            'require-dev': ['vendor/package'],
        })


if __name__ == '__main__':
    unittest.main()
