"""Validate every ancestor of nested npm installed packages, not just the leaf."""

import json
import unittest

from devpilot.npm_lock import parse_npm_lock


class NpmLockNestedSegmentTests(unittest.TestCase):
    def test_rejects_invalid_ancestor_package_names_privately(self):
        for path in (
            'node_modules/https:secret/node_modules/legit',
            'node_modules/@scope/node_modules/legit',
            'node_modules/valid/extra/node_modules/legit',
            'packages/app/node_modules/valid/other/node_modules/legit',
        ):
            with self.subTest(path=path):
                content = json.dumps({'packages': {path: {}}})
                with self.assertRaises(ValueError) as caught:
                    parse_npm_lock(content)
                self.assertNotIn('secret', str(caught.exception))
                self.assertNotIn('https', str(caught.exception))
                self.assertNotIn(path, str(caught.exception))

    def test_accepts_valid_scoped_and_unscoped_nested_paths(self):
        content = json.dumps({'packages': {
            '': {}, 'packages/app': {},
            'packages/app/node_modules/@scope/parent/node_modules/dep': {},
            'node_modules/parent/node_modules/@scope/child': {},
            'node_modules/top': {},
        }})
        self.assertEqual(parse_npm_lock(content), ['@scope/child', 'dep', 'top'])


if __name__ == '__main__':
    unittest.main()
