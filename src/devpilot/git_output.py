"""Safe human-readable rendering of Git's porcelain status and diagnostics."""

from __future__ import annotations

from typing import Any

from .console import escape_terminal


def format_git_status(report: dict[str, Any]) -> str:
    """Render Git status safely and disclose failed or incomplete inspections.

    Preserve porcelain record separators in stdout, but never trust diagnostic
    line breaks. When command capture is truncated or Git fails, clearly mark
    the output as incomplete instead of presenting a misleading clean status.
    JSON reports retain their original data unchanged.
    """
    stdout = report.get('stdout')
    rendered = ('\n'.join(escape_terminal(line) for line in str(stdout).split('\n'))
                if stdout else '')
    diagnostic = report.get('error') or report.get('stderr')
    warnings: list[str] = []

    if report.get('stdout_truncated'):
        warnings.append('Warning: Git status output truncated; results may be incomplete')
    if report.get('stderr_truncated'):
        warnings.append('Warning: Git diagnostic output truncated; details may be incomplete')

    if 'exit_code' in report and report['exit_code'] != 0:
        code = report['exit_code']
        if code is None:
            warnings.append('Git status unavailable (command did not complete)')
        else:
            warnings.append(f'Git status failed (exit code {escape_terminal(str(code))})')
        if diagnostic:
            warnings.append(escape_terminal(str(diagnostic)))
    elif report.get("dirty", False) is None and "dirty" in report:
        warnings.append("Git status unavailable (worktree state inconclusive)")
    elif not stdout and report.get("dirty") is True:
        warnings.append("Git status reports changes but output is unavailable")
    elif not stdout and diagnostic:
        warnings.append(escape_terminal(str(diagnostic)))

    if warnings:
        return '\n'.join(([rendered.rstrip('\n')] if rendered else []) + warnings)
    return rendered or 'No changes'
