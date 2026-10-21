"""Canonicalize an already-validated TLS peer name for certificate matching."""

from __future__ import annotations


def tls_server_name(dial_host: str) -> str:
    """Canonicalize a DNS or IPv6 dial target for certificate verification.

    DNS root dots are not part of certificate names. Likewise, an IPv6 zone
    identifier (e.g. ``%eth0``) selects a local interface for dialing, not an
    address component that can appear in an IP-address certificate SAN.
    Keep the original host for TCP resolution and reports. The caller must
    validate the host before using this helper.
    """
    if ':' in dial_host:
        return dial_host.partition('%')[0]
    if dial_host.endswith('.'):
        return dial_host[:-1]
    return dial_host
