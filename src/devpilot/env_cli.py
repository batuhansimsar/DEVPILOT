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

    This is also a public formatting boundary: reject malformed external
    reports before iterating or escaping their potentially hostile fields.
    """
    invalid = 'Environment: invalid environment report'
    if type(result) is not dict:
        return invalid
    status = result.get('status')
    if type(status) is not str:
        return invalid
    if status == 'no_template':
        return 'Environment: no ' + ', '.join(TEMPLATES) + ' found'

    if status == 'missing_keys':
        missing_keys = result.get('missing_keys')
        if type(missing_keys) not in (list, tuple) or not missing_keys or any(
            type(key) is not str for key in missing_keys
        ):
            return invalid
        missing = ', '.join(escape_terminal(key) for key in missing_keys)
        return f'Environment: names missing from .env: {missing} (may be supplied externally)'

    if status not in ('matched', 'local_absent', 'unreadable_template', 'unreadable_local'):
        return invalid
    template = result.get('template')
    if type(template) is not str:
        return invalid
    if status == 'matched':
        return (f"Environment: all {_safe_count(result.get('expected_count'))} names in "
                f"{escape_terminal(template)} declared in .env (values not checked)")
    if status == 'local_absent':
        return (f"Environment: {escape_terminal(template)} declares "
                f"{_safe_count(result.get('expected_count'))} names; local .env is absent")
    detail = result.get('detail')
    if type(detail) is not str:
        return invalid
    return (f"Environment: unable to inspect {escape_terminal(template)} "
            f"or .env ({escape_terminal(detail)})")
