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
    invalid_stdout = stdout is not None and not isinstance(stdout, str)
    rendered = ('\n'.join(escape_terminal(line) for line in stdout.split('\n'))
                if isinstance(stdout, str) and stdout else '')
    # A command can produce both a capture/spawn error and Git's stderr.
    # Keep distinct diagnostics, safely escaped, instead of silently dropping
    # stderr when the error field is nonempty.
    diagnostics = tuple(dict.fromkeys(
        escape_terminal(str(value)) for value in (report.get('error'), report.get('stderr'))
        if value
    ))
    warnings: list[str] = []

    if invalid_stdout:
        warnings.append('Git status unavailable (invalid porcelain output)')
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
        warnings.extend(diagnostics)
    elif report.get("dirty", False) is None and "dirty" in report:
        warnings.append("Git status unavailable (worktree state inconclusive)")
    elif not stdout and report.get("dirty") is True:
        warnings.append("Git status reports changes but output is unavailable")
    elif not stdout and report.get('exit_code') == 0 and 'dirty' not in report:
        # --porcelain=v1 --branch always prints a branch header, even for a
        # clean worktree. Missing output without an explicit clean verdict is
        # incomplete, not evidence that the repository has no changes.
        warnings.append('Git status unavailable (empty porcelain output)')
    elif not stdout and diagnostics:
        warnings.extend(diagnostics)

    # A successful exit can still carry Git warnings (such as repository
    # configuration or filesystem diagnostics). Do not silently discard them
    # when porcelain stdout is available, and never trust their line breaks.
    if report.get('exit_code') == 0 and stdout:
        warnings.extend('Git diagnostic: ' + message for message in diagnostics)

    if warnings:
        return '\n'.join(([rendered.rstrip('\n')] if rendered else []) + warnings)
    return rendered or 'No changes'
