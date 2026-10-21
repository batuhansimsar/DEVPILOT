"""Bound resource use when probing caller-supplied HTTP endpoints."""

from __future__ import annotations

import ipaddress
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
# Resolver implementations may interpret shortened, octal or hexadecimal
# numeric names as IPv4 literals (e.g. 127.1 -> 127.0.0.1). Do not let a
# diagnostic probe connect to an address different from the one displayed.
_LEGACY_IPV4_LABEL = re.compile(rb'(?:[0-9]+|0[xX][0-9A-Fa-f]+)\Z')


def validate_dns_hostname_labels(hostname: bytes) -> None:
    """Require DNS host-label syntax before opening an HTTP connection.

    Python's IDNA encoder checks label lengths and empty labels but permits
    illegal host characters and leading or trailing hyphens. The caller passes
    an IDNA-encoded DNS hostname or canonical IPv4 literal. An optional trailing dot
    is allowed; errors never echo untrusted hostnames.
    """
    if not isinstance(hostname, bytes):
        raise ValueError('URL host contains an invalid DNS label')
    # Enforce the complete wire-form DNS hostname limit, not just per-label size.
    # A trailing root dot occupies one additional byte in textual form.
    if len(hostname) > (254 if hostname.endswith(b'.') else 253):
        raise ValueError('URL host exceeds DNS hostname length limit')
    labels = hostname[:-1].split(b'.') if hostname.endswith(b'.') else hostname.split(b'.')
    if any(len(label) > 63 or _DNS_LABEL.fullmatch(label) is None for label in labels):
        raise ValueError('URL host contains an invalid DNS label')
    # Permit canonical dotted-decimal IPv4 (handled by the same HTTP probe),
    # but reject ambiguous all-numeric DNS names before an OS resolver can
    # reinterpret them as legacy IPv4 addresses. Avoid DNS/network lookups.
    if len(labels) <= 4 and all(_LEGACY_IPV4_LABEL.fullmatch(label) for label in labels):
        try:
            canonical_ipv4 = ipaddress.IPv4Address(hostname.decode('ascii'))
        except ValueError:
            canonical_ipv4 = None
        if canonical_ipv4 is None or str(canonical_ipv4).encode('ascii') != hostname:
            raise ValueError('URL host contains an ambiguous IPv4 address')
