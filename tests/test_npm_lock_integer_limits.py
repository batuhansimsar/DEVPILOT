"""Reject oversized JSON integers consistently without disclosing lock metadata."""

import json
import unittest

from devpilot.npm_lock import parse_npm_lock


class NpmLockIntegerLimitTests(unittest.TestCase):
    def test_oversized_positive_and_negative_integer_metadata_are_rejected(self):
        for value in ('9' * 5000, '-' + '9' * 5000):
            with self.subTest(sign=value[0]):
                content = ('{"private_token":"do-not-disclose",'
                           '"packages":{"node_modules/react":{}},"counter":' + value + '}')
                with self.assertRaisesRegex(ValueError, 'oversized integer') as raised:
                    parse_npm_lock(content)
                self.assertNotIn('do-not-disclose', str(raised.exception))
                self.assertNotIn(value, str(raised.exception))

    def test_ordinary_numeric_metadata_keeps_package_inventory(self):
        content = json.dumps({'lockfileVersion': 3, 'counter': -42,
                              'packages': {'node_modules/react': {},
                                           'node_modules/@scope/pkg': {}}})
        self.assertEqual(parse_npm_lock(content), ['@scope/pkg', 'react'])

    def test_large_but_bounded_json_integer_does_not_break_inventory(self):
        content = ('{"metadata":' + ('9' * 1024) + ',"packages":'
                   '{"node_modules/react":{}}}')
        self.assertEqual(parse_npm_lock(content), ['react'])


if __name__ == '__main__':
    unittest.main()
