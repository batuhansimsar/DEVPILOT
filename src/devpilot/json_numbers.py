"""Strict, privacy-safe validation of JSON floating-point values."""

from __future__ import annotations

import math


def parse_finite_json_float(value: str) -> float:
    """Reject numbers that overflow Python floats without exposing input text.

    JSON syntax permits arbitrarily large exponents, but silently converting
    them to infinities makes otherwise-valid JSON manifests non-finite.
    Use as ``json.loads(..., parse_float=parse_finite_json_float)``.
    """
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('non-finite JSON number')
    return number
