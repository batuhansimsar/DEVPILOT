"""Presentation and exit status for explicit environment key checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .envcheck import inspect_env


def environment_status(root: Path) -> tuple[dict[str, Any], bool]:
    """Inspect declared variable *names*; absence of local files is advisory."""
    result = inspect_env(root)
    return result, result['status'] in ('matched', 'local_absent', 'no_template')


def format_environment(result: dict[str, Any]) -> str:
    """Render variable names and counts, never environment variable values."""
    status = result['status']
    if status == 'matched':
        return f"Environment: all {result['expected_count']} names in {result['template']} declared in .env (values not checked)"
    if status == 'missing_keys':
        return f"Environment: names missing from .env: {', '.join(result['missing_keys'])} (may be supplied externally)"
    if status == 'local_absent':
        return f"Environment: {result['template']} declares {result['expected_count']} names; local .env is absent"
    if status == 'no_template':
        return 'Environment: no .env.example, .env.sample, or .env.template found'
    return f"Environment: unable to inspect {result['template']} or .env ({result['detail']})"
