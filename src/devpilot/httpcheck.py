"""Explicit, bounded HTTP health checks with redirects disabled."""

from __future__ import annotations

import re
import time
from itertools import islice
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import HTTPHandler, HTTPSHandler, HTTPRedirectHandler, ProxyHandler, Request, build_opener


_INVALID_PERCENT_ESCAPE = re.compile(r'%(?![0-9A-Fa-f]{2})')


def _encode_component(value: str, *, safe: str) -> str:
    """Preserve valid percent escapes while encoding stray '%' and Unicode."""
    return quote(_INVALID_PERCENT_ESCAPE.sub('%25', value), safe=safe)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        return None


def http_check(url: str, timeout: float = 3.0, *, expected_statuses: frozenset[int] | None = None, method: str = 'HEAD') -> dict:
    """Probe an explicitly supplied URL using HEAD, without reading response bodies.

    When supplied, expected_statuses replaces the default healthy 2xx range,
    allowing expected 401/403 responses from protected endpoints.
    """
    if method not in ('HEAD', 'GET'):
        raise ValueError('method must be HEAD or GET')
    if not isinstance(url, str):
        raise ValueError('URL must be a string')
    # urlsplit silently strips leading spaces and certain control characters;
    # reject raw whitespace and controls so the target matches the supplied URL.
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in url):
        # Keep this raw-input guard: urlsplit may silently strip controls.
        # Differentiate an invalid hostname from a malformed path/query.
        try:
            invalid_host = urlsplit(url).hostname
        except ValueError:
            invalid_host = None
        if invalid_host and any(char.isspace() for char in invalid_host):
            raise ValueError('URL host must not contain whitespace or backslashes')
        raise ValueError('URL must not contain whitespace or control characters')
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname or '@' in parts.netloc:
        raise ValueError('URL must be an absolute http(s) URL without credentials')
    # urllib needs an ASCII authority; internationalized paths and queries
    # can instead be encoded without changing the requested host.
    if not parts.netloc.isascii():
        raise ValueError('URL host must be ASCII (use IDNA for internationalized hostnames)')
    # Percent-encoded authority bytes can be interpreted differently by URL
    # parsers and DNS libraries. Require a literal, unambiguous hostname.
    if '%' in parts.netloc:
        raise ValueError('URL host must not contain percent escapes')
    if any(char.isspace() for char in parts.hostname) or '\\' in parts.hostname:
        raise ValueError('URL host must not contain whitespace or backslashes')
    if (not isinstance(timeout, (int, float)) or isinstance(timeout, bool)
            or not 0.1 <= timeout <= 30):
        raise ValueError('timeout must be between 0.1 and 30 seconds')
    if expected_statuses is not None:
        # Capture once: generators would otherwise be exhausted by validation,
        # causing membership checks to reject even an expected response.
        # At most 500 distinct HTTP status codes exist, so bound consumption.
        try:
            statuses = tuple(islice(iter(expected_statuses), 501))
        except (TypeError, ValueError):
            statuses = ()
        if not statuses or len(statuses) > 500 or not all(
            type(code) is int and 100 <= code <= 599 for code in statuses
        ):
            raise ValueError('expected HTTP status codes must be between 100 and 599')
        expected_statuses = frozenset(statuses)
    try:
        port = parts.port
    except ValueError as exc:
        raise ValueError('URL contains an invalid port') from exc
    if port == 0 or (port is None and parts.netloc.endswith(':')):
        raise ValueError('URL port must be between 1 and 65535')
    # urlsplit.hostname omits IPv6 brackets; put them back for valid display URLs.
    host = f'[{parts.hostname}]' if ':' in parts.hostname else parts.hostname
    display = f'{parts.scheme}://{host}' + (f':{port}' if port is not None else '') + (_encode_component(parts.path, safe="/%:@!$&'()*+,;=-._~") or '/')
    # Health checks must measure the requested endpoint, not an ambient proxy.
    opener = build_opener(ProxyHandler({}), HTTPHandler(), HTTPSHandler(), _NoRedirect())
    # Encode Unicode path/query data as UTF-8 without double-encoding existing
    # percent escapes. Keep only an ASCII, percent-encoded path in reports.
    request_url = urlunsplit((
        parts.scheme, parts.netloc,
        _encode_component(parts.path, safe="/%:@!$&'()*+,;=-._~"),
        _encode_component(parts.query, safe="/?%:@!$&'()*+,;=-._~"),
        '',
    ))
    request = Request(request_url, method=method, headers={'User-Agent': 'DevPilot/0.1'})
    start = time.monotonic()
    try:
        with opener.open(request, timeout=timeout) as response:
            status = response.status
    except HTTPError as exc:
        status = exc.code  # 3xx, 4xx and 5xx are valid HTTP responses, not network failures.
        exc.close()
    except (URLError, OSError, TimeoutError) as exc:
        return {'url': display, 'method': method, 'reachable': False, 'status': None, 'healthy': False,
                'latency_ms': round((time.monotonic() - start) * 1000, 1),
                'error': type(exc).__name__}
    # A redirect is reachable, but not healthy: following it is deliberately disabled.
    return {'url': display, 'method': method, 'reachable': True, 'status': status, 'healthy': (status in expected_statuses if expected_statuses is not None else 200 <= status < 300),
            'latency_ms': round((time.monotonic() - start) * 1000, 1)}
