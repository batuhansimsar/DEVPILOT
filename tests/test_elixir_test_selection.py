"""Elixir test discovery must be selectable through the same CLI as other ecosystems."""

import unittest

from devpilot.test_selection import ECOSYSTEMS, select_test_commands


class ElixirTestSelectionTests(unittest.TestCase):
    def test_elixir_is_a_supported_test_filter(self):
        self.assertEqual(ECOSYSTEMS['elixir'], 'Elixir')

    def test_selects_only_elixir_commands_without_mutating_plan(self):
        commands = [
            {'ecosystem': 'Go', 'argv': ['go', 'test', './...'], 'reason': 'go.mod'},
            {'ecosystem': 'Elixir', 'argv': ['mix', 'test'], 'reason': 'mix.exs'},
        ]
        selected = select_test_commands(commands, 'elixir')
        self.assertEqual(selected, [commands[1]])
        selected[0]['argv'].append('--trace')
        self.assertEqual(commands[1]['argv'], ['mix', 'test'])
        self.assertEqual(select_test_commands(commands, 'ELIXIR'), [commands[1]])

    def test_cli_parser_accepts_elixir_filter(self):
        from devpilot.cli import build_parser

        args = build_parser().parse_args(['test', '--ecosystem', 'elixir'])
        self.assertEqual(args.command, 'test')
        self.assertEqual(args.ecosystem, 'elixir')


if __name__ == '__main__':
    unittest.main()
