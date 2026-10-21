"""Decide whether bounded repository scans can be reported as successful."""

from __future__ import annotations

from typing import Any, Mapping


def scan_succeeded(report: Mapping[str, Any]) -> bool:
    """Fail closed if a scan is incomplete or has malformed diagnostics.

    A truncated inventory is not evidence that the omitted entries are safe.
    Require an explicit boolean ``truncated=False``, a real empty list of
    problems, and no recorded error. Missing or malformed diagnostics must
    never imply success.
    """
    # Public callers may pass a missing or malformed scan report. Do not
    # mistake such a result for success or raise while interpreting it.
    if not isinstance(report, Mapping):
        return False
    try:
        problems = report.get('problems')
        truncated = report.get('truncated')
        error = report.get('error')
    except Exception:
        # Custom mappings can raise while reading untrusted diagnostic keys.
        # If their contents cannot be inspected, the scan is not successful.
        return False
    return truncated is False and type(problems) is list and not problems and error is None
