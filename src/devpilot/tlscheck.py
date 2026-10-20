"""Explicit, certificate-verifying TLS health checks for developer services."""

from __future__ import annotations

import datetime
import socket
import ssl
import time
from typing import Any


def tls_check(host: str, port: int, timeout: float) -> dict[str, Any]:
    """Check TCP then a trusted TLS handshake; never disable certificate validation.

    ``reachable`` means the requested TLS protocol is healthy. ``tcp_reachable``
    distinguishes a refused connection from a TLS or certificate failure.
    ``tcp_latency_ms`` and ``tls_handshake_ms`` help locate a slow phase without
    changing the existing total ``latency_ms`` or certificate verification.
    """
    if not isinstance(host, str) or not host or any(
        char.isspace() or ord(char) < 32 or ord(char) == 127 for char in host
    ):
        raise ValueError('host must be a hostname or IP address without whitespace')
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('port must be between 1 and 65535')
    if (not isinstance(timeout, (int, float)) or isinstance(timeout, bool)
            or not 0.1 <= timeout <= 30):
        raise ValueError('timeout must be between 0.1 and 30 seconds')
    start = time.monotonic()
    result: dict[str, Any] = {
        'host': host, 'port': port, 'reachable': False,
        'tcp_reachable': False, 'tls_valid': False,
    }
    tcp_start = time.perf_counter()
    try:
        connection = socket.create_connection((host, port), timeout=timeout)
    except (OSError, TimeoutError) as exc:
        result['tcp_latency_ms'] = round((time.perf_counter() - tcp_start) * 1000, 1)
        result['error'] = str(exc)
        result['latency_ms'] = round((time.monotonic() - start) * 1000, 1)
        return result

    # Preserve a single socket timeout budget across TCP connect and TLS handshake.
    # Otherwise both stages can consume the full user-specified timeout.
    tcp_elapsed = time.perf_counter() - tcp_start
    result['tcp_latency_ms'] = round(tcp_elapsed * 1000, 1)
    result['tcp_reachable'] = True
    with connection:
        try:
            context = ssl.create_default_context()
            # Certificate-store initialization also consumes the shared timeout.
            # Recalculate immediately before negotiating TLS, not before SSL setup.
            remaining = timeout - (time.perf_counter() - tcp_start)
            if remaining <= 0:
                raise TimeoutError('TLS handshake timeout exhausted before negotiation')
            connection.settimeout(remaining)
            handshake_start = time.perf_counter()
            try:
                secured_connection = context.wrap_socket(connection, server_hostname=host)
            finally:
                # A failed handshake is still useful timing information.
                result['tls_handshake_ms'] = round((time.perf_counter() - handshake_start) * 1000, 1)
            with secured_connection as secured:
                certificate = secured.getpeercert()
                result['tls_valid'] = True
                result['reachable'] = True
                if certificate and certificate.get('notAfter'):
                    expires = datetime.datetime.fromtimestamp(
                        ssl.cert_time_to_seconds(certificate['notAfter']),
                        tz=datetime.timezone.utc,
                    )
                    result['expires_at'] = expires.isoformat().replace('+00:00', 'Z')
                    remaining_seconds = (expires - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
                    result['expires_in_days'] = max(0, int(remaining_seconds // 86400))
                    result['expires_soon'] = remaining_seconds <= 30 * 86400
        except (ssl.SSLError, OSError, ValueError, OverflowError) as exc:
            result['error'] = str(exc)
    result['latency_ms'] = round((time.monotonic() - start) * 1000, 1)
    return result
