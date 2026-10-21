"""Prevent DNS probes from silently rewriting Unicode hostnames via IDNA."""

from __future__ import annotations

import unicodedata


def ensure_unambiguous_idna_hostname(hostname: str, encoded: bytes) -> None:
    """Reject lossy IDNA mappings while allowing Unicode case/NFC normalization.

    Python's built-in IDNA (2003) codec maps some printable characters to
    entirely different DNS names (e.g. ``faß.de`` to ``fass.de``). A diagnostic
    probe must not silently connect to a different name than the requested one.
    ASCII hosts, including explicit punycode A-labels, must also agree with
    the encoded dial target (case-insensitively).
    """
    if not isinstance(hostname, str) or not isinstance(encoded, bytes):
        raise ValueError('host contains an ambiguous IDNA hostname')
    if hostname.isascii():
        # The IDNA decoder intentionally maps valid ASCII A-labels to Unicode.
        # Compare ASCII input directly instead; skipping this check could let
        # a caller dial an unrelated hostname while reporting the original.
        if hostname.lower().encode('ascii') != encoded.lower():
            raise ValueError('host contains an ambiguous IDNA hostname')
        return
    try:
        canonical = encoded.decode('idna')
    except UnicodeError:
        raise ValueError('host contains an ambiguous IDNA hostname') from None
    if unicodedata.normalize('NFC', hostname).lower() != canonical.lower():
        raise ValueError('host contains an ambiguous IDNA hostname')
