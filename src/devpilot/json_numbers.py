"""Strict, privacy-safe validation of JSON floating-point values."""

from __future__ import annotations

import math


def parse_finite_json_float(value: str) -> float:
    """Reject invalid or overflowing floats without exposing the input text.

    JSON decoding supplies syntactically valid numeric tokens, but direct callers
    may pass malformed values. Never allow float() conversion errors to echo
    untrusted input (which could contain private manifest data).
    """
    try:
        number = float(value)
    except (ValueError, OverflowError):
        raise ValueError('invalid JSON number') from None
    if not math.isfinite(number):
        raise ValueError('non-finite JSON number')
    return number
