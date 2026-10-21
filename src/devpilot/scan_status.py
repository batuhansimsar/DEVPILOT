"""Decide whether bounded repository scans can be reported as successful."""

from __future__ import annotations

from typing import Any, Mapping


def scan_succeeded(report: Mapping[str, Any]) -> bool:
    """Fail closed when a scan is incomplete, even without other problems.

    A truncated inventory is not evidence that the omitted entries are safe.
    Require an explicit boolean ``truncated=False`` in the scan report so a
    malformed or missing field cannot silently report success to CI.
    """
    return report.get('truncated') is False and not report.get('problems')
