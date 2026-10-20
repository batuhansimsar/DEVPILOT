"""Safe human-readable rendering of Git's porcelain status and diagnostics."""

from __future__ import annotations

from typing import Any

from .console import escape_terminal


def format_git_status(report: dict[str, Any]) -> str:
    """Render Git porcelain records safely without allowing diagnostic line spoofing.

    Git porcelain uses LF to separate records. Preserve structural LF only for
    status stdout; arbitrary error messages are not records and must escape
    embedded line breaks as well as terminal controls. JSON reports deliberately
    retain the original, unmodified command output.
    """
    stdout = report.get('stdout')
    if stdout:
        return '\n'.join(escape_terminal(line) for line in str(stdout).split('\n'))

    diagnostic = report.get('error') or report.get('stderr')
    if diagnostic:
        return escape_terminal(str(diagnostic))
    if report.get('exit_code') not in (None, 0) or ('dirty' in report and report['dirty'] is None):
        return 'Git status unavailable'
    return 'No changes'
