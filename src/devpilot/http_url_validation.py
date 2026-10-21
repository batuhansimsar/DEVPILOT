"""Bound resource use when probing caller-supplied HTTP endpoints."""

from __future__ import annotations

MAX_HTTP_URL_LENGTH = 8192


def validate_http_url_length(url: str) -> None:
    """Reject exceptionally long URLs before parsing or network setup.

    The limit bounds URI parsing, quoting, logging and request construction;
    validation messages never repeat potentially sensitive URL contents.
    """
    if not isinstance(url, str):
        raise ValueError('URL must be a string')
    if len(url) > MAX_HTTP_URL_LENGTH:
        raise ValueError(f'URL exceeds {MAX_HTTP_URL_LENGTH}-character limit')
