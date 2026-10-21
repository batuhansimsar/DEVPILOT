"""Invalid test selectors do not disclose raw caller input."""

import unittest

from devpilot.test_selection import select_test_commands


class TestSelectionInputPrivacyTests(unittest.TestCase):
    def test_unknown_alias_does_not_appear_in_key_error(self):
        secret = 'private-token-0123456789'
        with self.assertRaises(KeyError) as error:
            select_test_commands([], secret)
        self.assertNotIn(secret, str(error.exception))
        self.assertEqual(error.exception.args, ('unknown test ecosystem',))

    def test_unexpected_types_rejected_without_reflection(self):
        for invalid in (123, True, ['python'], {'key': 'python'}):
            with self.subTest(kind=type(invalid).__name__):
                with self.assertRaises(KeyError) as error:
                    select_test_commands([], invalid)
                self.assertEqual(error.exception.args, ('unknown test ecosystem',))

    def test_known_aliases_and_none_keep_copy_isolation(self):
        commands = [{'ecosystem': 'Python', 'argv': ['python', '-m', 'unittest']}]
        for selected in (select_test_commands(commands, 'PyThOn'), select_test_commands(commands, None)):
            self.assertEqual(selected, commands)
            selected[0]['argv'].append('modified')
        self.assertEqual(commands[0]['argv'], ['python', '-m', 'unittest'])


if __name__ == '__main__':
    unittest.main()
