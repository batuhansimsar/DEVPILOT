"""Explicit, bounded HTTP health checks with redirects disabled."""

from __future__ import annotations

from .http_url_validation import validate_dns_hostname_labels, validate_http_url_length

import ipaddress
import re
from http.client import HTTPException
import time
from itertools import islice
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import HTTPHandler, HTTPSHandler, HTTPRedirectHandler, ProxyHandler, Request, build_opener


_INVALID_PERCENT_ESCAPE = re.compile(r'%(?![0-9A-Fa-f]{2})')
# Bound raw and percent-encoded request targets before sending network traffic.
MAX_HTTP_URL_LENGTH = 8192


def _encode_component(value: str, *, safe: str) -> str:
    """Preserve valid percent escapes while encoding stray '%' and Unicode."""
    return quote(_INVALID_PERCENT_ESCAPE.sub('%25', value), safe=safe)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        return None


def http_check(url: str, timeout: float = 3.0, *, expected_statuses: frozenset[int] | None = None, method: str = 'HEAD') -> dict:
    """Probe an explicit URL with HEAD, GET, or OPTIONS, without reading response bodies.

    When supplied, expected_statuses replaces the default healthy 2xx range,
    allowing expected 401/403 responses from protected endpoints.
    """
    if method not in ('HEAD', 'GET', 'OPTIONS'):
        raise ValueError('method must be HEAD, GET or OPTIONS')
    validate_http_url_length(url)
    # A giant input should not reach URL parsing, escaping, or the network.
    if len(url) > MAX_HTTP_URL_LENGTH:
        raise ValueError('URL exceeds 8192 character limit')
    # Lone UTF-16 surrogates cannot be encoded as UTF-8 for the request target.
    # Reject them before building an opener or triggering a low-level encoding
    # exception that might expose parts of the user-supplied URL.
    if any(0xD800 <= ord(char) <= 0xDFFF for char in url):
        raise ValueError('URL must not contain unpaired Unicode surrogates')
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
    try:
        # urlsplit may echo untrusted host text for malformed IPv6 brackets or
        # authorities containing Unicode characters that normalize to delimiters.
        parts = urlsplit(url)
    except ValueError:
        raise ValueError('URL contains an invalid authority') from None
    if parts.scheme not in ('http', 'https') or not parts.hostname or '@' in parts.netloc:
        raise ValueError('URL must be an absolute http(s) URL without credentials')
    # urlsplit accepts IPvFuture literals in square brackets, but urllib's
    # transport does not support them, and the report would omit brackets.
    # Reject trailing authority garbage as well, before any networking.
    if parts.netloc.startswith('['):
        try:
            ipaddress.IPv6Address(parts.hostname)
        except ValueError:
            raise ValueError('URL host must be a valid bracketed IPv6 address') from None
        closing = parts.netloc.find(']')
        remainder = parts.netloc[closing + 1:]
        if remainder and not remainder.startswith(':'):
            raise ValueError('URL host contains an invalid bracketed IPv6 authority')
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
    # Reject malformed/overlong DNS labels before urllib starts a request.
    # Otherwise socket IDNA encoding can raise an uncaught UnicodeError.
    try:
        idna_hostname = parts.hostname.encode('idna')
    except UnicodeError:
        raise ValueError('URL host contains an invalid IDNA hostname') from None
    # The IDNA codec checks each label but not the full DNS hostname size.
    # A complete name may contain at most 253 text bytes (254 with a final dot).
    if len(idna_hostname) > (254 if idna_hostname.endswith(b'.') else 253):
        raise ValueError('URL host exceeds DNS hostname length limit')
    # IDNA accepts punctuation and boundary hyphens that are not valid DNS host labels.
    if ':' not in parts.hostname:  # Bracketed IPv6 literals use ':' and are validated above.
        validate_dns_hostname_labels(idna_hostname)
    if (not isinstance(timeout, (int, float)) or isinstance(timeout, bool)
            or not 0.1 <= timeout <= 30):
        raise ValueError('timeout must be between 0.1 and 30 seconds')
    if expected_statuses is not None:
        # Capture once: generators would otherwise be exhausted by validation,
        # causing membership checks to reject even an expected response.
        # At most 500 distinct HTTP status codes exist, so bound consumption.
        try:
            statuses = tuple(islice(iter(expected_statuses), 501))
        except Exception:
            # An arbitrary iterator can raise any Exception (including OSError).
            # Reject it without exposing its private error text or attempting I/O.
            statuses = ()
        if not statuses or len(statuses) > 500 or not all(
            type(code) is int and 100 <= code <= 599 for code in statuses
        ):
            raise ValueError('expected HTTP status codes must be between 100 and 599')
        expected_statuses = frozenset(statuses)
    try:
        port = parts.port
    except ValueError:
        # urllib's port error can include the raw, potentially sensitive text.
        raise ValueError('URL contains an invalid port') from None
    if port == 0 or (port is None and parts.netloc.endswith(':')):
        raise ValueError('URL port must be between 1 and 65535')
    # urlsplit.hostname omits IPv6 brackets; put them back for valid display URLs.
    host = f'[{parts.hostname}]' if ':' in parts.hostname else parts.hostname
    display = f'{parts.scheme}://{host}' + (f':{port}' if port is not None else '') + (_encode_component(parts.path, safe="/%:@!$&'()*+,;=-._~") or '/')
    # Health checks must measure the requested endpoint, not an ambient proxy.
    # Encode Unicode path/query data as UTF-8 without double-encoding existing
    # percent escapes. Keep only an ASCII, percent-encoded path in reports.
    request_url = urlunsplit((
        parts.scheme, parts.netloc,
        _encode_component(parts.path, safe="/%:@!$&'()*+,;=-._~"),
        _encode_component(parts.query, safe="/?%:@!$&'()*+,;=-._~"),
        '',
    ))
    # Percent encoding can expand short Unicode input into a much larger URL.
    if len(request_url) > MAX_HTTP_URL_LENGTH:
        raise ValueError('Encoded URL exceeds 8192 character limit')
    opener = build_opener(ProxyHandler({}), HTTPHandler(), HTTPSHandler(), _NoRedirect())
    request = Request(request_url, method=method, headers={'User-Agent': 'DevPilot/0.1'})
    start = time.monotonic()
    try:
        with opener.open(request, timeout=timeout) as response:
            status = response.status
    except HTTPError as exc:
        status = exc.code  # 3xx, 4xx and 5xx are valid HTTP responses, not network failures.
        exc.close()
    except (URLError, OSError, TimeoutError, HTTPException) as exc:
        return {'url': display, 'method': method, 'reachable': False, 'status': None, 'healthy': False,
                'latency_ms': round((time.monotonic() - start) * 1000, 1),
                'error': type(exc).__name__}
    # Malformed HTTP responses and custom transports can expose a missing or
    # non-integer status. Reject them before comparisons or JSON serialization.
    # bool is an int subclass but never a valid HTTP status code.
    if type(status) is not int or not 100 <= status <= 599:
        return {'url': display, 'method': method, 'reachable': False, 'status': None, 'healthy': False,
                'latency_ms': round((time.monotonic() - start) * 1000, 1),
                'error': 'InvalidHTTPStatus'}
    # A redirect is reachable, but not healthy: following it is deliberately disabled.
    return {'url': display, 'method': method, 'reachable': True, 'status': status, 'healthy': (status in expected_statuses if expected_statuses is not None else 200 <= status < 300),
            'latency_ms': round((time.monotonic() - start) * 1000, 1)}
