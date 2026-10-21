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
    has_stdout = isinstance(stdout, str) and bool(stdout)
    exit_code_present = 'exit_code' in report
    exit_code = report.get('exit_code')
    exit_succeeded = type(exit_code) is int and exit_code == 0
    rendered = ('\n'.join(escape_terminal(line) for line in stdout.split('\n'))
                if isinstance(stdout, str) and stdout else '')
    # Do not call __str__, __repr__, or __bool__ on malformed runner values:
    # diagnostic objects may embed secrets, raise, or have side effects.
    # Preserve each actual string diagnostic and report other types generically.
    diagnostic_messages: list[str] = []
    for value in (report.get('error'), report.get('stderr')):
        if isinstance(value, str):
            if value:
                diagnostic_messages.append(escape_terminal(value))
        elif value is not None:
            diagnostic_messages.append('unreadable non-text diagnostic')
    diagnostics = tuple(dict.fromkeys(diagnostic_messages))
    warnings: list[str] = []

    if invalid_stdout:
        warnings.append('Git status unavailable (invalid porcelain output)')
    # Capture flags are trusted only when they are actual booleans. Coercing
    # malformed runner values could invoke arbitrary __bool__ methods, and
    # silently interpreting them as false would misrepresent incomplete data.
    for key, warning in (
        ('stdout_truncated', 'Warning: Git status output truncated; results may be incomplete'),
        ('stderr_truncated', 'Warning: Git diagnostic output truncated; details may be incomplete'),
    ):
        flag = report.get(key, False)
        if flag is True:
            warnings.append(warning)
        elif flag is not False:
            warnings.append(f'Warning: invalid Git {key} flag; output may be incomplete')

    # An invalid worktree verdict must never silently look clean. Avoid
    # truth-value coercion of unexpected runner objects (which can raise or
    # produce side effects), and do not expose their text in diagnostics.
    dirty_present = 'dirty' in report
    dirty = report.get('dirty')
    if dirty_present and dirty is not None and type(dirty) is not bool:
        warnings.append('Git status unavailable (invalid worktree state)')

    if exit_code_present and not exit_succeeded:
        code = exit_code
        if code is None:
            warnings.append('Git status unavailable (command did not complete)')
        elif type(code) is not int:
            warnings.append('Git status unavailable (invalid exit code)')
        else:
            warnings.append(f'Git status failed (exit code {code})')
    elif dirty_present and dirty is None:
        warnings.append("Git status unavailable (worktree state inconclusive)")
    elif not has_stdout and dirty is True:
        warnings.append("Git status reports changes but output is unavailable")
    elif not has_stdout and not invalid_stdout and exit_succeeded:
        # --porcelain=v1 --branch always prints a branch header, even for a
        # clean worktree. A separate dirty=False verdict cannot make missing
        # output complete, so never report "No changes" without that header.
        warnings.append('Git status unavailable (empty porcelain output)')
    elif not has_stdout and not invalid_stdout and not exit_code_present and not diagnostics:
        # A missing process result is not proof of a clean worktree. Preserve
        # diagnostic-only reports for backwards compatibility.
        warnings.append('Git status unavailable (missing command result)')

    # A successful exit can still carry Git warnings (such as repository
    # configuration or filesystem diagnostics). Do not silently discard them
    # when porcelain stdout is available, and never trust their line breaks.
    if exit_succeeded and has_stdout:
        warnings.extend('Git diagnostic: ' + message for message in diagnostics)
    elif not has_stdout or (exit_code_present and not exit_succeeded):
        # Failure and missing-output states must retain diagnostics as well.
        warnings.extend(diagnostics)

    if warnings:
        return '\n'.join(([rendered.rstrip('\n')] if rendered else []) + warnings)
    return rendered or 'No changes'
