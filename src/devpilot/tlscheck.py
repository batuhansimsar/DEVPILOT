"""Explicit, certificate-verifying TLS health checks for developer services."""

from __future__ import annotations

import datetime
import socket
import ssl
from typing import Any


def tls_check(host: str, port: int, timeout: float) -> dict[str, Any]:
    """Check TCP then a trusted TLS handshake; never disable certificate validation.

    ``reachable`` means the requested TLS protocol is healthy. ``tcp_reachable``
    distinguishes a refused connection from a TLS or certificate failure.
    """
    if not 1 <= port <= 65535:
        raise ValueError('port must be between 1 and 65535')
    result: dict[str, Any] = {
        'host': host, 'port': port, 'reachable': False,
        'tcp_reachable': False, 'tls_valid': False,
    }
    try:
        connection = socket.create_connection((host, port), timeout=timeout)
    except (OSError, TimeoutError) as exc:
        result['error'] = str(exc)
        return result

    result['tcp_reachable'] = True
    with connection:
        try:
            context = ssl.create_default_context()
            with context.wrap_socket(connection, server_hostname=host) as secured:
                certificate = secured.getpeercert()
                result['tls_valid'] = True
                result['reachable'] = True
                if certificate and certificate.get('notAfter'):
                    expires = datetime.datetime.fromtimestamp(
                        ssl.cert_time_to_seconds(certificate['notAfter']),
                        tz=datetime.timezone.utc,
                    )
                    result['expires_at'] = expires.isoformat().replace('+00:00', 'Z')
        except (ssl.SSLError, OSError, ValueError, OverflowError) as exc:
            result['error'] = str(exc)
    return result
