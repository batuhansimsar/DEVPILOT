"""User-facing language names are valid aliases for test ecosystem selection."""

import argparse
import unittest

from devpilot.test_selection import ECOSYSTEMS, ECOSYSTEM_ALIASES, select_test_commands


class LanguageAliasTests(unittest.TestCase):
    def setUp(self):
        self.commands = [
            {'ecosystem': 'Node.js', 'argv': ['npm', 'test']},
            {'ecosystem': 'C/C++', 'argv': ['ctest', '--test-dir', 'build']},
            {'ecosystem': 'Go', 'argv': ['go', 'test', './...']},
        ]

    def test_language_aliases_select_expected_runner(self):
        for alias in ('js', 'javascript', 'ts', 'typescript'):
            with self.subTest(alias=alias):
                self.assertEqual(select_test_commands(self.commands, alias), [self.commands[0]])
        for alias in ('c++', 'c/c++', 'cxx'):
            with self.subTest(alias=alias):
                self.assertEqual(select_test_commands(self.commands, alias), [self.commands[1]])

    def test_cli_choice_parsing_accepts_aliases_and_case_insensitivity(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--ecosystem', type=str.casefold,
                            choices=(*ECOSYSTEMS, *ECOSYSTEM_ALIASES))
        for value in ('JavaScript', 'TypeScript', 'C++', 'C/C++'):
            with self.subTest(value=value):
                name = parser.parse_args(['--ecosystem', value]).ecosystem
                self.assertEqual(len(select_test_commands(self.commands, name)), 1)

    def test_alias_selection_does_not_mutate_discovery(self):
        chosen = select_test_commands(self.commands, 'TypeScript')
        chosen[0]['argv'].append('changed')
        self.assertEqual(self.commands[0]['argv'], ['npm', 'test'])

    def test_unknown_alias_does_not_leak_value(self):
        with self.assertRaises(KeyError) as error:
            select_test_commands(self.commands, 'private-unknown-token')
        self.assertEqual(error.exception.args, ('unknown test ecosystem',))


if __name__ == '__main__':
    unittest.main()
