"""Regression coverage for C-family test-runner aliases."""

import argparse
import unittest

from devpilot.test_selection import ECOSYSTEMS, ECOSYSTEM_ALIASES, select_test_commands


class CFamilyLanguageAliasTests(unittest.TestCase):
    def test_aliases_select_cpp_runner_without_mutating_discovery(self):
        commands = [
            {'ecosystem': 'C/C++', 'argv': ['ctest', '--test-dir', 'build']},
            {'ecosystem': 'Python', 'argv': ['python', '-m', 'pytest']},
        ]
        for alias in ('c', 'C', 'c++', 'C/C++', 'C/CPP', 'CXX', 'CPlusPlus'):
            with self.subTest(alias=alias):
                selected = select_test_commands(commands, alias)
                self.assertEqual(selected, [commands[0]])
                self.assertIsNot(selected[0], commands[0])
                selected[0]['argv'].append('--extra')
                self.assertEqual(commands[0]['argv'], ['ctest', '--test-dir', 'build'])

    def test_cli_parser_accepts_new_aliases(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--ecosystem', type=str.casefold,
                            choices=(*ECOSYSTEMS, *ECOSYSTEM_ALIASES))
        for alias in ('C', 'C/CPP', 'CPlusPlus'):
            with self.subTest(alias=alias):
                args = parser.parse_args(['--ecosystem', alias])
                self.assertEqual(ECOSYSTEM_ALIASES[args.ecosystem], 'cpp')

    def test_unrelated_languages_remain_filtered_out(self):
        commands = [{'ecosystem': 'Go', 'argv': ['go', 'test', './...']}]
        self.assertEqual(select_test_commands(commands, 'c'), [])
        with self.assertRaises(KeyError):
            select_test_commands(commands, 'c-language-invalid')


if __name__ == '__main__':
    unittest.main()
