"""Haskell test commands are selectable through the CLI ecosystem flag."""

import unittest

from devpilot.test_selection import ECOSYSTEMS, select_test_commands


class HaskellTestSelectionTests(unittest.TestCase):
    def test_haskell_choice_maps_to_discovered_stack_and_cabal_commands(self):
        commands = [
            {'ecosystem': 'Go', 'argv': ['go', 'test', './...']},
            {'ecosystem': 'Haskell', 'argv': ['stack', 'test']},
            {'ecosystem': 'Haskell', 'argv': ['cabal', 'test']},
        ]
        self.assertEqual(ECOSYSTEMS['haskell'], 'Haskell')
        selected = select_test_commands(commands, 'haskell')
        self.assertEqual([command['argv'] for command in selected],
                         [['stack', 'test'], ['cabal', 'test']])
        selected[0]['argv'].append('--fast')
        self.assertEqual(commands[1]['argv'], ['stack', 'test'])

    def test_haskell_filter_is_case_insensitive_and_excludes_unrelated_tests(self):
        commands = [
            {'ecosystem': 'Go', 'argv': ['go', 'test', './...']},
            {'ecosystem': 'Haskell', 'argv': ['stack', 'test']},
        ]
        self.assertEqual(select_test_commands(commands, 'HASKELL'), [commands[1]])
        self.assertEqual(select_test_commands(commands, 'go'), [commands[0]])
        self.assertTrue(select_test_commands(commands, 'haskell'))


if __name__ == '__main__':
    unittest.main()
