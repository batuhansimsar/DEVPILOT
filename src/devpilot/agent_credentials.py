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
    ('.codex', 'auth.json'),  # Codex CLI login tokens and authentication state.
})


# Claude Code project-local settings can contain environment variables with
# embedded credentials; unlike generic settings.json, the local-only filename
# is a useful signal of potentially sensitive tracked configuration.
_AGENT_LOCAL_SETTINGS = frozenset({
    ('.claude', 'settings.local.json'),
})


# MCP server definitions may include API keys in environment variables and
# HTTP headers. Scope ambiguous names to known editor directories; the portable
# .mcp.json convention has its own distinctive basename.
_MCP_CONFIG_LOCATIONS = frozenset({
    ('.cursor', 'mcp.json'),
    ('.vscode', 'mcp.json'),
    ('.copilot', 'mcp-config.json'),
    # Codex CLI MCP server definitions can embed bearer tokens in env/headers.
    ('.codex', 'config.toml'),
})


# Claude Code user-local and Claude Desktop MCP settings can contain
# API keys in env variables or HTTP authorization headers. Exact names keep
# unrelated JSON documents and sample templates out of manual audit reports.
_MCP_CONFIG_NAMES = frozenset({
    '.mcp.json', '.claude.json', 'claude_desktop_config.json',
})

def is_agent_credential_location(parts: tuple[str, ...]) -> bool:
    """Match conventional private token stores, not arbitrary JSON files."""
    return len(parts) >= 2 and parts[-2:] in _AGENT_CREDENTIAL_LOCATIONS


def is_agent_local_settings(parts: tuple[str, ...]) -> bool:
    """Identify local assistant settings that may contain plaintext secrets."""
    return len(parts) >= 2 and parts[-2:] in _AGENT_LOCAL_SETTINGS


def is_agent_mcp_config(parts: tuple[str, ...]) -> bool:
    """Flag MCP configurations for manual secret review without opening them."""
    return bool(parts) and (parts[-1] in _MCP_CONFIG_NAMES or (
        len(parts) >= 2 and parts[-2:] in _MCP_CONFIG_LOCATIONS
    ))
