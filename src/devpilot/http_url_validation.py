"""Bound resource use when probing caller-supplied HTTP endpoints."""

from __future__ import annotations

import re

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


_DNS_LABEL = re.compile(rb'[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\Z')


def validate_dns_hostname_labels(hostname: bytes) -> None:
    """Require DNS host-label syntax before opening an HTTP connection.

    Python's IDNA encoder checks label lengths and empty labels but permits
    illegal host characters and leading or trailing hyphens. The caller passes
    an IDNA-encoded DNS hostname, not an IP literal. An optional trailing dot
    is allowed; errors never echo untrusted hostnames.
    """
    labels = hostname[:-1].split(b'.') if hostname.endswith(b'.') else hostname.split(b'.')
    if any(len(label) > 63 or _DNS_LABEL.fullmatch(label) is None for label in labels):
        raise ValueError('URL host contains an invalid DNS label')
