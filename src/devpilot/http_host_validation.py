"""Validate IDNA-encoded DNS labels before starting an HTTP probe."""

from __future__ import annotations

_ASCII_ALNUM = frozenset(b'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
_ASCII_LABEL = _ASCII_ALNUM | frozenset(b'-')


def validate_http_dns_labels(hostname: bytes) -> None:
    """Reject malformed DNS host labels without exposing caller input.

    Input is the ASCII/IDNA representation of a *DNS* host, not an IPv6
    literal. A single trailing root dot is allowed. Validate the complete
    name too, so direct callers cannot bypass the ordinary IDNA size checks.
    """
    if not isinstance(hostname, bytes):
        raise ValueError('URL host contains an invalid DNS label')
    labels = (hostname[:-1] if hostname.endswith(b'.') else hostname).split(b'.')
    if (len(hostname) > (254 if hostname.endswith(b'.') else 253)
            or any(not label or len(label) > 63
                   or label[0] not in _ASCII_ALNUM or label[-1] not in _ASCII_ALNUM
                   or any(char not in _ASCII_LABEL for char in label)
                   for label in labels)):
        raise ValueError('URL host contains an invalid DNS label')
