"""AI coding assistant credentials are recognized without broad JSON matches."""

import unittest

from devpilot.agent_credentials import is_agent_credential_location


class AgentCredentialPathTests(unittest.TestCase):
    def test_known_token_store_locations(self):
        for path in (
            ('.claude', '.credentials.json'),
            ('home', 'user', '.claude', '.credentials.json'),
            ('.gemini', 'oauth_creds.json'),
            ('project', 'home', '.gemini', 'oauth_creds.json'),
        ):
            with self.subTest(path=path):
                self.assertTrue(is_agent_credential_location(path))

    def test_unrelated_files_and_templates_are_not_token_stores(self):
        for path in (
            (), ('auth.json',), ('docs', '.credentials.json'),
            ('docs', 'oauth_creds.json'),
            ('.claude', 'settings.json'),
            ('.claude', '.credentials.json.example'),
            ('.gemini', 'oauth_creds.json.sample'),
            ('.gemini', 'settings.json'),
            ('gemini', 'oauth_creds.json'),
        ):
            with self.subTest(path=path):
                self.assertFalse(is_agent_credential_location(path))


if __name__ == '__main__':
    unittest.main()
