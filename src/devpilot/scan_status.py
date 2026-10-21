"""Decide whether bounded repository scans can be reported as successful."""

from __future__ import annotations

from typing import Any, Mapping


def scan_succeeded(report: Mapping[str, Any]) -> bool:
    """Fail closed unless the scan explicitly completed with no problems.

    A truncated inventory is not evidence that omitted entries are safe.
    Likewise, a missing or malformed ``problems`` field cannot establish
    that the scan found no issues. Both analyze and workspace reports use
    a list for this field; do not mistake other falsey values for an empty
    list when deciding the CLI exit status.
    """
    if not isinstance(report, Mapping):
        return False
    problems = report.get('problems')
    return report.get('truncated') is False and isinstance(problems, list) and not problems
