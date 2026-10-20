"""Regression coverage for safe npm lockfile version validation."""

import json
import unittest

from devpilot.npm_lock import parse_npm_lock


class NpmLockVersionTests(unittest.TestCase):
    def test_supported_versions_keep_existing_inventory_behavior(self):
        for version in (1, 2, 3):
            with self.subTest(version=version):
                content = json.dumps({
                    'lockfileVersion': version,
                    'packages': {'': {}, 'node_modules/@scope/example': {'version': '1.0'}},
                })
                self.assertEqual(parse_npm_lock(content), ['@scope/example'])

    def test_legacy_lockfile_without_version_is_accepted(self):
        self.assertEqual(
            parse_npm_lock('{"dependencies":{"example":{"version":"1"}}}'),
            ['example'],
        )

    def test_invalid_version_is_rejected_without_exposing_metadata(self):
        invalid = ('true', 'false', 'null', '"3"', '3.0', '0', '-1', '4', '{}', '[]')
        for version in invalid:
            with self.subTest(version=version):
                content = ('{"lockfileVersion":' + version + ',"packages":{},'
                           '"resolved":"https://user:secret@registry.invalid"}')
                with self.assertRaises(ValueError) as error:
                    parse_npm_lock(content)
                self.assertEqual(
                    str(error.exception), 'npm lockfile has an unsupported lockfileVersion',
                )
                self.assertNotIn('secret', str(error.exception))


if __name__ == '__main__':
    unittest.main()
