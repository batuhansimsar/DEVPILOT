"""Regression tests for CLI ecosystem aliases."""

import unittest

from devpilot.test_selection import ECOSYSTEMS, ECOSYSTEM_ALIASES, select_test_commands


class EcosystemAliasTests(unittest.TestCase):
    def setUp(self):
        self.commands = [
            {'ecosystem': 'Node.js', 'argv': ['npm', 'test']},
            {'ecosystem': 'Python', 'argv': ['python', '-m', 'unittest']},
            {'ecosystem': 'Go', 'argv': ['go', 'test', './...']},
            {'ecosystem': '.NET', 'argv': ['dotnet', 'test']},
        ]

    def test_aliases_select_matching_ecosystem(self):
        for alias, label in (
            ('node.js', 'Node.js'), ('NODEJS', 'Node.js'),
            ('Py', 'Python'), ('GOLANG', 'Go'),
            ('.NET', '.NET'), ('C#', '.NET'), ('csharp', '.NET'),
        ):
            with self.subTest(alias=alias):
                found = select_test_commands(self.commands, alias)
                self.assertEqual(len(found), 1)
                self.assertEqual(found[0]['ecosystem'], label)
                self.assertIsNot(found[0], next(c for c in self.commands if c['ecosystem'] == label))

    def test_aliases_resolve_to_known_canonical_keys(self):
        self.assertFalse(set(ECOSYSTEM_ALIASES).intersection(ECOSYSTEMS))
        self.assertTrue(set(ECOSYSTEM_ALIASES.values()).issubset(ECOSYSTEMS))

    def test_unknown_aliases_do_not_silently_select_tests(self):
        for value in ('node.js.evil', '.NET.NET', 'Python extra', 123, ''):
            with self.subTest(value=value), self.assertRaisesRegex(KeyError, 'unknown test ecosystem'):
                select_test_commands(self.commands, value)


class EcosystemAliasCLIParserTests(unittest.TestCase):
    def test_cli_accepts_case_insensitive_aliases(self):
        from devpilot.cli import build_parser

        parser = build_parser()
        for alias in ('node.js', 'NODEJS', 'Py', 'GOLANG', '.NET', 'C#', 'csharp'):
            with self.subTest(alias=alias):
                args = parser.parse_args(['test', '--ecosystem', alias])
                self.assertEqual(args.ecosystem, alias.casefold())


if __name__ == '__main__':
    unittest.main()
