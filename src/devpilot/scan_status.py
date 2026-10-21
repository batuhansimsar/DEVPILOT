"""Decide whether bounded repository scans can be reported as successful."""

from __future__ import annotations

from typing import Any, Mapping


def scan_succeeded(report: Mapping[str, Any]) -> bool:
    """Fail closed if a scan is incomplete or has a malformed problem list.

    A truncated inventory is not evidence that the omitted entries are safe.
    Require an explicit boolean ``truncated=False`` and a real, empty list of
    problems. Missing, null, or non-list diagnostics must never imply success.
    """
    problems = report.get('problems')
    return report.get('truncated') is False and type(problems) is list and not problems
