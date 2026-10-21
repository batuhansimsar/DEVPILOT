"""Recognize token stores used by AI coding assistants from their paths.

No credential contents are inspected. The owning audits normalize case,
separators, and editor backup suffixes before calling these predicates.
"""

from __future__ import annotations

_AGENT_CREDENTIAL_LOCATIONS = frozenset({
    ('.claude', '.credentials.json'),  # Claude Code OAuth credentials.
    ('.gemini', 'oauth_creds.json'),  # Gemini CLI OAuth credentials.
    # Gemini CLI persists per-MCP-server OAuth access and refresh tokens here.
    ('.gemini', 'mcp-oauth-tokens.json'),
})


# MCP server definitions may include API keys in environment variables and
# HTTP headers. Scope ambiguous names to known editor directories; the portable
# .mcp.json convention has its own distinctive basename.
_MCP_CONFIG_LOCATIONS = frozenset({
    ('.cursor', 'mcp.json'),
    ('.vscode', 'mcp.json'),
    ('.copilot', 'mcp-config.json'),
})


def is_agent_credential_location(parts: tuple[str, ...]) -> bool:
    """Match conventional private token stores, not arbitrary JSON files."""
    return len(parts) >= 2 and parts[-2:] in _AGENT_CREDENTIAL_LOCATIONS


def is_agent_mcp_config(parts: tuple[str, ...]) -> bool:
    """Flag MCP configurations for manual secret review without opening them."""
    return bool(parts) and (parts[-1] == '.mcp.json' or (
        len(parts) >= 2 and parts[-2:] in _MCP_CONFIG_LOCATIONS
    ))
