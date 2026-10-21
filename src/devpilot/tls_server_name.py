"""Canonicalize an already-validated TLS peer name for certificate matching."""

from __future__ import annotations


def tls_server_name(dial_host: str) -> str:
    """Remove an optional DNS root dot for SNI and certificate verification.

    DNS accepts ``example.org.`` as an absolute form of ``example.org``, but
    certificates normally list the latter. Keep the original input for TCP
    resolution and user-facing reports. IPv6 literals are never rewritten.
    The caller must validate the host before using this helper.
    """
    if dial_host.endswith('.') and ':' not in dial_host:
        return dial_host[:-1]
    return dial_host
