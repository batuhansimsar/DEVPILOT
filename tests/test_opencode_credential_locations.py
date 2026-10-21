"""OpenCode token locations must be recognized without reading their contents."""

import unittest

from devpilot.agent_credentials import is_agent_credential_location


class OpenCodeCredentialLocationTests(unittest.TestCase):
    def test_provider_and_mcp_auth_files_and_version_2_database(self):
        for path in (
            ('opencode', 'auth.json'),
            ('home', 'user', '.local', 'share', 'opencode', 'auth.json'),
            ('data', 'opencode', 'mcp-auth.json'),
            ('home', 'user', '.local', 'share', 'opencode', 'opencode.db'),
        ):
            with self.subTest(path=path):
                self.assertTrue(is_agent_credential_location(path))

    def test_unrelated_databases_and_templates_are_not_token_stores(self):
        for path in (
            (), ('auth.json',), ('opencode.db',),
            ('data', 'opencode.db'),
            ('data', 'mcp-auth.json'),
            ('opencode', 'auth.json.example'),
            ('opencode', 'mcp-auth.json.sample'),
            ('opencode', 'opencode.db.template'),
            ('opencode', 'sessions.db'),
            ('other-tool', 'opencode.db'),
        ):
            with self.subTest(path=path):
                self.assertFalse(is_agent_credential_location(path))


if __name__ == '__main__':
    unittest.main()
