import unittest

from devpilot.test_execution import execute_test_commands
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

    def test_filtered_selection_is_independent_of_discovered_commands(self):
        self.commands[1]['metadata'] = {'hints': ['go.mod']}
        selected = select_test_commands(self.commands, 'go')
        selected[0]['argv'].append('-count=1')
        selected[0]['metadata']['hints'].append('edited')
        selected[0]['result'] = {'exit_code': 1}
        self.assertEqual(self.commands[1]['argv'], ['go', 'test', './...'])
        self.assertEqual(self.commands[1]['metadata'], {'hints': ['go.mod']})
        self.assertNotIn('result', self.commands[1])

    def test_unfiltered_selection_execution_does_not_annotate_discovery(self):
        from pathlib import Path
        selected = select_test_commands(self.commands, None)
        self.assertTrue(execute_test_commands(
            selected, Path('/tmp/project'), 5,
            lambda argv, root, timeout: {'exit_code': 0},
        ))
        self.assertTrue(all('result' in command for command in selected))
        self.assertTrue(all('result' not in command for command in self.commands))
        selected[0]['argv'][0] = 'other-command'
        self.assertEqual(self.commands[0]['argv'], ['npm', 'test'])


if __name__ == '__main__':
    unittest.main()
