"""Strict, privacy-safe validation of JSON floating-point values."""

from __future__ import annotations

import math
import re

# float() accepts Python-only forms such as '+1', '.5', '1_', or '1_000'.
# Validate the actual JSON number grammar before conversion, including for
# direct callers that do not go through json.loads().
_JSON_NUMBER = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z')
# Manifest scanners already bound file sizes, but a single JSON numeric token
# could consume almost the whole limit. Reject excessively long float strings
# before regex matching or conversion, including calls outside the scanner.
MAX_JSON_FLOAT_CHARS = 4096


def parse_finite_json_float(value: str) -> float:
    """Convert only finite, bounded JSON numbers without leaking input."""
    if (not isinstance(value, str) or len(value) > MAX_JSON_FLOAT_CHARS
            or _JSON_NUMBER.fullmatch(value) is None):
        raise ValueError('invalid JSON number')
    try:
        number = float(value)
    except (ValueError, OverflowError):
        raise ValueError('invalid JSON number') from None
    if not math.isfinite(number):
        raise ValueError('non-finite JSON number')
    return number
