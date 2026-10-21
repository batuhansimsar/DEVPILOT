"""Presentation and exit status for explicit environment key checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .console import escape_terminal
from .envcheck import TEMPLATES, inspect_env


def environment_status(root: Path) -> tuple[dict[str, Any], bool]:
    """Inspect declared variable *names*; absence of local files is advisory."""
    result = inspect_env(root)
    return result, result['status'] in ('matched', 'local_absent', 'no_template')


def _safe_count(value: object) -> str:
    """Only render nonnegative integer counts from potentially forged reports."""
    return str(value) if type(value) is int and value >= 0 else 'unknown'


def format_environment(result: dict[str, Any]) -> str:
    """Render variable names and counts safely, never environment values.

    This is also a public formatting boundary: escape untrusted metadata even
    when the report was produced by another caller rather than inspect_env().
    """
    status = result['status']
    if status == 'matched':
        return (f"Environment: all {_safe_count(result['expected_count'])} names in "
                f"{escape_terminal(result['template'])} declared in .env (values not checked)")
    if status == 'missing_keys':
        missing = ', '.join(escape_terminal(key) for key in result['missing_keys'])
        return f"Environment: names missing from .env: {missing} (may be supplied externally)"
    if status == 'local_absent':
        return (f"Environment: {escape_terminal(result['template'])} declares "
                f"{_safe_count(result['expected_count'])} names; local .env is absent")
    if status == 'no_template':
        return 'Environment: no ' + ', '.join(TEMPLATES) + ' found'
    return (f"Environment: unable to inspect {escape_terminal(result['template'])} "
            f"or .env ({escape_terminal(result['detail'])})")
