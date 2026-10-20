"""Case-insensitive ecosystem selection should preserve command isolation."""

import unittest

from devpilot.test_selection import select_test_commands


class EcosystemAliasesTests(unittest.TestCase):
    def test_mixed_case_aliases_select_same_commands(self):
        commands = [
            {'ecosystem': 'Go', 'argv': ['go', 'test', './...']},
            {'ecosystem': 'Node.js', 'argv': ['npm', 'test']},
            {'ecosystem': '.NET', 'argv': ['dotnet', 'test']},
        ]
        for key, expected in [('Go', 'Go'), ('GO', 'Go'), ('NoDe', 'Node.js'), ('DOTNET', '.NET')]:
            with self.subTest(key=key):
                selected = select_test_commands(commands, key)
                self.assertEqual(len(selected), 1)
                self.assertEqual(selected[0]['ecosystem'], expected)
                selected[0]['argv'].append('modified')
                self.assertNotIn('modified', str(commands))

    def test_unknown_ecosystem_is_still_rejected(self):
        with self.assertRaises(KeyError):
            select_test_commands([], 'UNKNOWN')


if __name__ == '__main__':
    unittest.main()
