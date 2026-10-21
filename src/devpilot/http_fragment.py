"""Reject URL fragments that HTTP clients silently omit from requests."""

from __future__ import annotations


def reject_http_fragment(url: str) -> None:
    """Keep a health check from probing a different URL than the user supplied.

    A literal ``#`` begins a fragment, which is never sent over HTTP. The
    percent-encoded path or query character ``%23`` is not a fragment.
    Call only after the URL has been checked to be a string and size-bounded.
    """
    if '#' in url:
        raise ValueError('URL fragments are not supported by HTTP health checks')
