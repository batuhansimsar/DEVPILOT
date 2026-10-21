"""Direct npm-lock parsing bounds UTF-8 bytes, not only Python characters."""

import unittest

from devpilot.npm_lock import MAX_NPM_LOCK_INPUT_BYTES, parse_npm_lock


class NpmLockUTF8BudgetTests(unittest.TestCase):
    def test_valid_json_at_exact_byte_limit(self):
        prefix = '{"lockfileVersion":3,"packages":{"node_modules/react":{}}}'
        content = prefix + ' ' * (MAX_NPM_LOCK_INPUT_BYTES - len(prefix))
        self.assertEqual(len(content.encode('utf-8')), MAX_NPM_LOCK_INPUT_BYTES)
        self.assertEqual(parse_npm_lock(content), ['react'])

    def test_multibyte_unicode_over_budget_is_rejected(self):
        content = '{"packages":{},"private":"' + 'é' * (MAX_NPM_LOCK_INPUT_BYTES // 2) + '"}'
        self.assertLess(len(content), MAX_NPM_LOCK_INPUT_BYTES)
        self.assertGreater(len(content.encode('utf-8')), MAX_NPM_LOCK_INPUT_BYTES)
        with self.assertRaisesRegex(ValueError, 'size limit') as raised:
            parse_npm_lock(content)
        self.assertNotIn('private', str(raised.exception))

    def test_unpaired_surrogate_is_rejected_without_echoing_input(self):
        with self.assertRaisesRegex(ValueError, 'valid Unicode') as raised:
            parse_npm_lock('{"private":"' + '\ud800' + '","packages":{}}')
        self.assertNotIn('private', str(raised.exception))


if __name__ == '__main__':
    unittest.main()
