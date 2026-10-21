"""Validate decoded TOML input limits before invoking a parser."""

from __future__ import annotations


def validate_utf8_toml_size(content: str, limit: int, error_message: str) -> None:
    """Enforce both character and UTF-8 byte limits with private errors.

    Callers may supply decoded Unicode directly rather than going through the
    size-limited filesystem reader. A character-only cap can admit up to four
    times as many UTF-8 bytes, and lone surrogates cannot be encoded as UTF-8.
    """
    if not isinstance(content, str) or len(content) > limit:
        raise ValueError(error_message)
    try:
        size = len(content.encode('utf-8'))
    except UnicodeEncodeError:
        raise ValueError(error_message) from None
    if size > limit:
        raise ValueError(error_message)
