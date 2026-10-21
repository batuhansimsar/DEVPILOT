"""Bound untrusted JSON nesting independently of the Python decoder version."""

from __future__ import annotations

MAX_JSON_DEPTH = 128


class JSONNestingError(ValueError):
    """JSON exceeds the explicit manifest nesting budget."""


def validate_json_nesting(content: str) -> None:
    """Check structural depth before decoding, ignoring quoted/escaped brackets.

    This is a constant-memory preflight, not a JSON syntax validator. The JSON
    decoder still checks syntax, duplicate keys and numeric values afterward.
    Python 3.14 can decode much deeper JSON than older versions, so relying on
    its recursion limit no longer provides a consistent resource boundary.
    """
    depth = 0
    in_string = False
    escaped = False
    for char in content:
        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in '[{':
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise JSONNestingError('JSON nesting exceeds parser limits')
        elif char in ']}':
            depth -= 1
