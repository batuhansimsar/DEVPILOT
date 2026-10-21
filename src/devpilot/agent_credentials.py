"""Recognize token stores used by AI coding assistants from their paths.

No credential contents are inspected. The owning audits normalize case,
separators, and editor backup suffixes before calling this predicate.
"""

from __future__ import annotations

_AGENT_CREDENTIAL_LOCATIONS = frozenset({
    ('.claude', '.credentials.json'),  # Claude Code OAuth credentials.
    ('.gemini', 'oauth_creds.json'),  # Gemini CLI OAuth credentials.
    # Gemini CLI persists per-MCP-server OAuth access and refresh tokens here.
    ('.gemini', 'mcp-oauth-tokens.json'),
})


def is_agent_credential_location(parts: tuple[str, ...]) -> bool:
    """Match conventional private token stores, not arbitrary JSON files."""
    return len(parts) >= 2 and parts[-2:] in _AGENT_CREDENTIAL_LOCATIONS
