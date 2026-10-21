"""Path-only audits should flag MCP configs which may embed API credentials."""

import unittest

from devpilot.agent_credentials import is_agent_mcp_config
from devpilot.audit import _potential_secret
from devpilot.secret_audit import classify


class MCPConfigAuditTests(unittest.TestCase):
    def test_known_mcp_configuration_paths(self):
        for path in (
            '.cursor/mcp.json', '.vscode/mcp.json', '.mcp.json',
            '.copilot/mcp-config.json', 'nested/.cursor/mcp.json',
            '.codex/config.toml', 'home/user/.codex/config.toml',
            'home/user/.vscode/mcp.json',
        ):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential MCP server configuration with embedded credentials')

    def test_backup_and_windows_paths(self):
        for path in (r'HOME\.CURSOR\MCP.JSON', '.vscode/mcp.json.bak',
                     '.mcp.json.~4~', '.copilot/mcp-config.json.swp',
                     r'HOME\.CODEX\CONFIG.TOML', '.codex/config.toml.bak'):
            with self.subTest(path=path):
                self.assertTrue(_potential_secret(path))
                self.assertEqual(classify(path), 'potential MCP server configuration with embedded credentials')

    def test_templates_and_unrelated_files_are_not_flagged(self):
        for path in ('docs/mcp.json', 'mcp.json', '.vscode/settings.json',
                     '.cursor/mcp.json.example', '.mcp.json.sample',
                     '.copilot/mcp-config.json.template',
                     'docs/mcp-config.json', '.codex/config.toml.example',
                     'docs/config.toml', 'codex/config.toml'):
            with self.subTest(path=path):
                self.assertFalse(_potential_secret(path))
                self.assertIsNone(classify(path))

    def test_helper_requires_known_exact_locations(self):
        self.assertTrue(is_agent_mcp_config(('.cursor', 'mcp.json')))
        self.assertTrue(is_agent_mcp_config(('.codex', 'config.toml')))
        self.assertTrue(is_agent_mcp_config(('projects', '.mcp.json')))
        self.assertFalse(is_agent_mcp_config(('docs', 'mcp.json')))
        self.assertFalse(is_agent_mcp_config(()))


if __name__ == '__main__':
    unittest.main()
