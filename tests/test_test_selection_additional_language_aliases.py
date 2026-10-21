"""Common C and CLR language names select their existing test runners."""

import argparse
import unittest

from devpilot.test_selection import ECOSYSTEMS, ECOSYSTEM_ALIASES, select_test_commands


class AdditionalLanguageAliasTests(unittest.TestCase):
    def setUp(self):
        self.commands = [
            {'ecosystem': 'C/C++', 'argv': ['ctest', '--test-dir', 'build']},
            {'ecosystem': '.NET', 'argv': ['dotnet', 'test']},
            {'ecosystem': 'Go', 'argv': ['go', 'test', './...']},
        ]

    def test_c_alias_routes_to_cpp_tests(self):
        self.assertEqual(select_test_commands(self.commands, 'C'), [self.commands[0]])

    def test_fsharp_and_visual_basic_aliases_route_to_dotnet(self):
        for alias in ('F#', 'fsharp', 'VB', 'VisualBasic'):
            with self.subTest(alias=alias):
                selected = select_test_commands(self.commands, alias)
                self.assertEqual(selected, [self.commands[1]])
                self.assertIsNot(selected[0], self.commands[1])

    def test_new_aliases_work_with_cli_choice_parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--ecosystem', type=str.casefold,
                            choices=(*ECOSYSTEMS, *ECOSYSTEM_ALIASES))
        for alias in ('C', 'F#', 'FSHARP', 'VB', 'VisualBasic'):
            with self.subTest(alias=alias):
                parsed = parser.parse_args(['--ecosystem', alias])
                self.assertEqual(len(select_test_commands(self.commands, parsed.ecosystem)), 1)

    def test_unrelated_ecosystems_stay_unselected(self):
        self.assertEqual(select_test_commands(self.commands, 'python'), [])
        with self.assertRaisesRegex(KeyError, 'unknown test ecosystem'):
            select_test_commands(self.commands, 'f#-private-token')


if __name__ == '__main__':
    unittest.main()
