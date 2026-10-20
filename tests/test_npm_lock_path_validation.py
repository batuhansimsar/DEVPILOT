"""Reject hostile npm lockfile paths without breaking nested packages."""

import json
import unittest

from devpilot.npm_lock import parse_npm_lock


class NpmLockPathValidationTests(unittest.TestCase):
    def test_rejects_unsafe_ancestor_and_workspace_paths(self):
        paths = (
            '../../node_modules/safe',
            'node_modules/secret/../node_modules/safe',
            '/node_modules/safe',
            'node_modules//safe',
            'node_modules/safe/',
            'node_modules\\safe',
            'packages/../workspace',
            'packages//workspace',
        )
        for path in paths:
            with self.subTest(path=path):
                content = json.dumps({'lockfileVersion': 3, 'packages': {'': {}, path: {}}})
                with self.assertRaises(ValueError) as caught:
                    parse_npm_lock(content)
                self.assertNotIn('secret', str(caught.exception))
                self.assertNotIn(path, str(caught.exception))

    def test_valid_nested_and_workspace_packages(self):
        packages = {
            '': {},
            'packages/frontend': {},
            'node_modules/@scope/parent': {},
            'node_modules/@scope/parent/node_modules/child': {},
            'packages/frontend/node_modules/@scope/tool': {},
        }
        self.assertEqual(parse_npm_lock(json.dumps({'packages': packages})),
                         ['@scope/parent', '@scope/tool', 'child'])


if __name__ == '__main__':
    unittest.main()
