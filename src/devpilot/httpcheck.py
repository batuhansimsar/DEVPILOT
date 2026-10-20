"""Explicit, bounded HTTP health checks with redirects disabled."""

from __future__ import annotations

import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPHandler, HTTPSHandler, HTTPRedirectHandler, Request, build_opener


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        return None


def http_check(url: str, timeout: float = 3.0) -> dict:
    """Probe an explicitly supplied URL using HEAD, without reading response bodies."""
    # urlsplit silently strips certain control characters; reject them before parsing
    # so the endpoint that is probed always matches the caller's supplied URL.
    if any(ord(char) < 32 or ord(char) == 127 for char in url):
        raise ValueError('URL must not contain control characters')
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname or '@' in parts.netloc:
        raise ValueError('URL must be an absolute http(s) URL without credentials')
    if not 0.1 <= timeout <= 30:
        raise ValueError('timeout must be between 0.1 and 30 seconds')
    try:
        port = parts.port
    except ValueError as exc:
        raise ValueError('URL contains an invalid port') from exc
    if port == 0:
        raise ValueError('URL port must be between 1 and 65535')
    # urlsplit.hostname omits IPv6 brackets; put them back for valid display URLs.
    host = f'[{parts.hostname}]' if ':' in parts.hostname else parts.hostname
    display = f'{parts.scheme}://{host}' + (f':{port}' if port is not None else '') + (parts.path or '/')
    opener = build_opener(HTTPHandler(), HTTPSHandler(), _NoRedirect())
    request = Request(url, method='HEAD', headers={'User-Agent': 'DevPilot/0.1'})
    start = time.monotonic()
    try:
        with opener.open(request, timeout=timeout) as response:
            status = response.status
    except HTTPError as exc:
        status = exc.code  # 3xx, 4xx and 5xx are valid HTTP responses, not network failures.
        exc.close()
    except (URLError, OSError, TimeoutError) as exc:
        return {'url': display, 'reachable': False, 'status': None,
                'latency_ms': round((time.monotonic() - start) * 1000, 1),
                'error': type(exc).__name__}
    # A redirect is reachable, but not healthy: following it is deliberately disabled.
    return {'url': display, 'reachable': True, 'status': status, 'healthy': 200 <= status < 300,
            'latency_ms': round((time.monotonic() - start) * 1000, 1)}
