"""Compatibility entry point for HTTP DNS label validation.

Use the shared URL validator as the single source of hostname policy so HTTP
callers cannot diverge on label boundaries, allowed characters, or size caps.
"""

from __future__ import annotations

from .http_url_validation import validate_dns_hostname_labels


def validate_http_dns_labels(hostname: bytes) -> None:
    """Validate an IDNA-encoded DNS hostname using the shared policy."""
    validate_dns_hostname_labels(hostname)
