import unittest

from devpilot.test_selection import ECOSYSTEMS, select_test_commands


class TestSelectionTests(unittest.TestCase):
    def setUp(self):
        self.commands = [
            {'ecosystem': 'Node.js', 'argv': ['npm', 'test']},
            {'ecosystem': 'Go', 'argv': ['go', 'test', './...']},
            {'ecosystem': '.NET', 'argv': ['dotnet', 'test']},
        ]

    def test_no_filter_preserves_all_and_does_not_mutate_list(self):
        selected = select_test_commands(self.commands, None)
        self.assertEqual(selected, self.commands)
        self.assertIsNot(selected, self.commands)

    def test_filter_selects_only_go(self):
        self.assertEqual(select_test_commands(self.commands, 'go'), [self.commands[1]])
        self.assertEqual(self.commands[0]['argv'], ['npm', 'test'])

    def test_dotnet_alias(self):
        self.assertEqual(select_test_commands(self.commands, 'dotnet'), [self.commands[2]])

    def test_unavailable_ecosystem_yields_no_commands(self):
        self.assertEqual(select_test_commands(self.commands, 'python'), [])

    def test_all_ecosystem_names_are_distinct(self):
        self.assertEqual(len(set(ECOSYSTEMS.values())), len(ECOSYSTEMS))

    def test_unknown_key_rejected(self):
        with self.assertRaises(KeyError):
            select_test_commands(self.commands, 'invalid')


if __name__ == '__main__':
    unittest.main()
