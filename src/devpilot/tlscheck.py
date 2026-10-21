"""Explicit, certificate-verifying TLS health checks for developer services."""

from __future__ import annotations

import datetime
import errno
import ipaddress
import socket
import ssl
import time
from typing import Any

from .tls_server_name import tls_server_name
from .http_url_validation import validate_dns_hostname_labels

# Bound raw input before scanning Unicode or invoking the IDNA codec. DNS
# names have much smaller wire limits, but IDNA can expand Unicode characters.
MAX_TLS_HOST_LENGTH = 1024


def _validate_host_length(host: object) -> None:
    """Reject unreasonably large hostnames without exposing their contents."""
    if isinstance(host, str) and len(host) > MAX_TLS_HOST_LENGTH:
        raise ValueError(f'host exceeds {MAX_TLS_HOST_LENGTH}-character limit')



class _TLSBudgetExhausted(TimeoutError):
    """A local timeout decision, distinct from external exception messages."""


def _safe_tls_error(error: BaseException) -> str:
    """Classify failures without echoing untrusted OS or TLS error details."""
    if isinstance(error, _TLSBudgetExhausted):
        return 'TLS handshake timeout budget exhausted before negotiation'
    if isinstance(error, ssl.SSLCertVerificationError):
        return 'certificate verification failed'
    if isinstance(error, ssl.SSLError):
        return 'TLS handshake failed'
    if isinstance(error, TimeoutError):
        return 'TLS handshake timed out'
    if isinstance(error, ConnectionRefusedError):
        return 'refused'
    if isinstance(error, OSError):
        return errno.errorcode.get(error.errno, 'network I/O error')
    return 'TLS validation failed'


def _tls_dial_host(host: str) -> str:
    """Validate a bare host, normalizing optional brackets around IPv6 literals.

    Reject URL-like values and embedded ports before any DNS or TCP activity.
    Keep the original input for reporting while dialing the normalized host.
    """
    _validate_host_length(host)
    if not isinstance(host, str) or not host or any(
        char.isspace() or not char.isprintable() for char in host
    ):
        raise ValueError('host must be a hostname or IP address without whitespace or control characters')
    if any(char in host for char in '/\\@?#'):
        raise ValueError('host must be a hostname or IP address, not a URL')

    dial_host = host
    if '[' in host or ']' in host:
        if not (host.startswith('[') and host.endswith(']')):
            raise ValueError('host has malformed IPv6 brackets')
        dial_host = host[1:-1]
        try:
            parsed = ipaddress.ip_address(dial_host)
        except ValueError:
            # ipaddress includes the untrusted host in its exception message.
            raise ValueError('bracketed host must be a valid IPv6 address') from None
        if not isinstance(parsed, ipaddress.IPv6Address):
            raise ValueError('bracketed host must be a valid IPv6 address')

    if ':' in dial_host:
        try:
            parsed = ipaddress.ip_address(dial_host)
        except ValueError:
            # Suppress the cause so tracebacks cannot disclose the input.
            raise ValueError('host contains an invalid IPv6 address or embedded port') from None
        if not isinstance(parsed, ipaddress.IPv6Address):
            raise ValueError('host contains an invalid IPv6 address or embedded port')
    else:
        # Socket name resolution performs IDNA encoding and can raise an
        # uncaught UnicodeEncodeError for invalid or oversized DNS labels.
        # Validate without network activity or echoing the supplied hostname.
        try:
            ascii_host = dial_host.encode('idna')
        except UnicodeError:
            raise ValueError('host contains an invalid IDNA hostname') from None
        # Share the HTTP hostname policy: DNS syntax alone is insufficient
        # because resolvers can reinterpret legacy IPv4 names (e.g. 127.1).
        # Keep the TLS-specific error privacy contract for CLI callers.
        try:
            validate_dns_hostname_labels(ascii_host)
        except ValueError:
            raise ValueError('host contains an invalid IDNA hostname') from None
    return dial_host


def tls_check(host: str, port: int, timeout: float) -> dict[str, Any]:
    """Check TCP then a trusted TLS handshake; never disable certificate validation.

    ``reachable`` means the requested TLS protocol is healthy. ``tcp_reachable``
    distinguishes a refused connection from a TLS or certificate failure.
    ``tcp_latency_ms`` and ``tls_handshake_ms`` help locate a slow phase without
    changing the existing total ``latency_ms`` or certificate verification.
    """
    dial_host = _tls_dial_host(host)
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
        connection = socket.create_connection((dial_host, port), timeout=timeout)
    except (OSError, TimeoutError) as exc:
        result['tcp_latency_ms'] = round((time.perf_counter() - tcp_start) * 1000, 1)
        result['error'] = 'TCP connection timed out' if isinstance(exc, TimeoutError) else _safe_tls_error(exc)
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
                raise _TLSBudgetExhausted
            connection.settimeout(remaining)
            handshake_start = time.perf_counter()
            try:
                secured_connection = context.wrap_socket(connection, server_hostname=tls_server_name(dial_host))
            finally:
                # A failed handshake is still useful timing information.
                result['tls_handshake_ms'] = round((time.perf_counter() - handshake_start) * 1000, 1)
            with secured_connection as secured:
                certificate = secured.getpeercert()
                result['tls_valid'] = True
                result['reachable'] = True
                # Report verified negotiation details without exposing certificate data.
                # Ignore absent or malformed socket metadata rather than adding
                # non-serializable objects to the CLI's JSON result.
                # Protocol and cipher details are optional metadata. Failure to
                # inspect them must not change the verified handshake result.
                try:
                    version = secured.version()
                except (OSError, ValueError, TypeError, AttributeError):
                    version = None
                if isinstance(version, str) and version:
                    result['tls_version'] = version
                try:
                    cipher = secured.cipher()
                except (OSError, ValueError, TypeError, AttributeError):
                    cipher = None
                if isinstance(cipher, tuple) and len(cipher) == 3:
                    cipher_name, _, cipher_bits = cipher
                    if isinstance(cipher_name, str) and cipher_name:
                        result['tls_cipher'] = cipher_name
                    if type(cipher_bits) is int and cipher_bits > 0:
                        result['tls_cipher_bits'] = cipher_bits
                # Optional certificate expiry metadata must not invalidate an
                # otherwise successfully verified TLS connection.
                expiry_text = certificate.get('notAfter') if isinstance(certificate, dict) else None
                if isinstance(expiry_text, str) and expiry_text:
                    try:
                        expires = datetime.datetime.fromtimestamp(
                            ssl.cert_time_to_seconds(expiry_text),
                            tz=datetime.timezone.utc,
                        )
                    except (ValueError, TypeError, OverflowError, OSError):
                        pass
                    else:
                        result['expires_at'] = expires.isoformat().replace('+00:00', 'Z')
                        remaining_seconds = (expires - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
                        result['expires_in_days'] = max(0, int(remaining_seconds // 86400))
                        result['expires_soon'] = remaining_seconds <= 30 * 86400
        except (ssl.SSLError, OSError, ValueError, OverflowError) as exc:
            result['error'] = _safe_tls_error(exc)
    result['latency_ms'] = round((time.monotonic() - start) * 1000, 1)
    return result
