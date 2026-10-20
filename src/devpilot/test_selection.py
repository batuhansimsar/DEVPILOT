"""Selection of discovered test commands for polyglot workspaces."""

from __future__ import annotations

from typing import Any

# Stable, case-independent CLI choices, separate from user-facing ecosystem labels.
ECOSYSTEMS = {
    'node': 'Node.js',
    'python': 'Python',
    'go': 'Go',
    'rust': 'Rust',
    'dotnet': '.NET',
    'java': 'Java',
}


def select_test_commands(commands: list[dict[str, Any]], ecosystem: str | None) -> list[dict[str, Any]]:
    """Return only the requested ecosystem's commands; never modify discovery results."""
    if ecosystem is None:
        return list(commands)
    return [command for command in commands if command['ecosystem'] == ECOSYSTEMS[ecosystem]]
