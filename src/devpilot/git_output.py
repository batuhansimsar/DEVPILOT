"""Safe human-readable rendering of Git's porcelain status and diagnostics."""

from __future__ import annotations

from typing import Any

from .console import escape_terminal


def format_git_status(report: dict[str, Any]) -> str:
    """Escape untrusted terminal controls while preserving Git's record lines.

    Git porcelain uses LF to separate records and prints quoted filenames.
    Preserve those structural newlines, but escape controls *within* lines.
    JSON reports deliberately retain the original, unmodified command output.
    """
    message = report.get('stdout') or report.get('error') or report.get('stderr') or 'No changes'
    return '\n'.join(escape_terminal(line) for line in str(message).split('\n'))
