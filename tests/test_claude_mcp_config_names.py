"""Claude MCP config files can contain live tokens and deserve review."""

import unittest

from devpilot.agent_credentials import is_agent_mcp_config
from devpilot.audit import _potential_secret


class ClaudeMCPConfigNameTests(unittest.TestCase):
    def test_detects_local_claude_code_and_desktop_config(self):
        for parts in (
            ('.claude.json',),
            ('home', '.claude.json'),
            ('settings', 'claude_desktop_config.json'),
            ('claude_desktop_config.json',),
            ('.mcp.json',),
        ):
            with self.subTest(parts=parts):
                self.assertTrue(is_agent_mcp_config(parts))
                self.assertTrue(_potential_secret('/'.join(parts)))

    def test_backups_are_detected_but_templates_are_not(self):
        for name in ('.claude.json.bak', 'claude_desktop_config.json.old'):
            with self.subTest(name=name):
                self.assertTrue(_potential_secret(name))
        for name in ('.claude.json.example', 'claude_desktop_config.json.sample'):
            with self.subTest(name=name):
                self.assertFalse(_potential_secret(name))

    def test_rejects_similar_but_noncredential_names(self):
        for parts in (
            (),
            ('claude.json',),
            ('.claude.json.example',),
            ('claude_desktop_config.json.sample',),
            ('some-mcp.json',),
            ('.claude', 'settings.json'),
        ):
            with self.subTest(parts=parts):
                self.assertFalse(is_agent_mcp_config(parts))


if __name__ == '__main__':
    unittest.main()
