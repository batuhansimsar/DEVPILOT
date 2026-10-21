"""Bound direct npm lockfile parser calls before JSON decoding."""

import json
import unittest

from devpilot.npm_lock import MAX_NPM_LOCK_INPUT_CHARS, parse_npm_lock


class NpmLockInputBoundsTests(unittest.TestCase):
    def test_rejects_non_string_inputs_with_a_redacted_value_error(self):
        for value in (None, b'{"packages": {}}', [], {}, 42):
            with self.subTest(type=type(value).__name__):
                with self.assertRaisesRegex(ValueError, 'input exceeds safe size limit'):
                    parse_npm_lock(value)

    def test_oversized_lockfile_is_rejected_before_parsing(self):
        content = '{"token":"sensitive-credential","padding":"' + (
            'a' * MAX_NPM_LOCK_INPUT_CHARS
        )
        with self.assertRaisesRegex(ValueError, 'input exceeds safe size limit') as raised:
            parse_npm_lock(content)
        self.assertNotIn('sensitive-credential', str(raised.exception))

    def test_under_limit_lockfile_keeps_normal_inventory(self):
        content = json.dumps({'lockfileVersion': 3, 'packages': {
            '': {}, 'node_modules/example': {},
        }})
        self.assertEqual(parse_npm_lock(content), ['example'])


if __name__ == '__main__':
    unittest.main()
