"""Codex CLI auth must be recognized without overmatching other JSON files."""

import unittest

from devpilot.agent_credentials import is_agent_credential_location


class CodexCredentialsTests(unittest.TestCase):
    def test_codex_token_locations(self):
        for path in (
            ('.codex', 'auth.json'),
            ('home', 'user', '.codex', 'auth.json'),
        ):
            with self.subTest(path=path):
                self.assertTrue(is_agent_credential_location(path))

    def test_unrelated_files_are_not_codex_token_stores(self):
        for path in (
            ('auth.json',),
            ('docs', 'auth.json'),
            ('codex', 'auth.json'),
            ('.codex', 'config.toml'),
            ('.codex', 'auth.json.example'),
            ('.codex', 'auth.json.sample'),
        ):
            with self.subTest(path=path):
                self.assertFalse(is_agent_credential_location(path))


if __name__ == '__main__':
    unittest.main()
