"""Regression tests for npm lockfile path normalization and redaction."""

import json
import unittest

from devpilot.npm_lock import parse_npm_lock


class NpmLockPathTests(unittest.TestCase):
    def test_rejects_traversal_and_empty_segments_without_leaking_names(self):
        for path in (
            'node_modules/../node_modules/secret-token',
            'node_modules/./node_modules/secret-token',
            'node_modules//node_modules/secret-token',
            '/node_modules/secret-token',
            'packages/../node_modules/secret-token',
            'node_modules/secret-token/',
        ):
            with self.subTest(path=path):
                content = json.dumps({'packages': {path: {'version': '1'}}})
                with self.assertRaisesRegex(ValueError, '^npm lockfile contains an invalid installed package path$') as caught:
                    parse_npm_lock(content)
                self.assertNotIn('secret-token', str(caught.exception))

    def test_accepts_nested_and_workspace_packages(self):
        content = json.dumps({'packages': {
            '': {}, 'packages/frontend': {},
            'node_modules/@scope/ui': {},
            'node_modules/@scope/ui/node_modules/react': {},
            'packages/frontend/node_modules/scheduler': {},
        }})
        self.assertEqual(parse_npm_lock(content), ['@scope/ui', 'react', 'scheduler'])


if __name__ == '__main__':
    unittest.main()
