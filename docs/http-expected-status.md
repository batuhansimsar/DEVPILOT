# Explicit HTTP status expectations

By default, `devpilot http` probes an explicitly supplied URL with a HEAD
request and treats HTTP 200–299 as healthy. Some checks, such as confirming
that a protected endpoint rejects unauthenticated requests, need a different
expected HTTP status.

Require HTTP 401:

```sh
devpilot http http://localhost:8080/private --expect-status 401 --json
```

Repeat `--expect-status` to accept any one of several codes:

```sh
devpilot http http://localhost:8080/private --expect-status 401 --expect-status 403
```

If this option is provided, **only** the explicitly listed status codes are
healthy. For example, if `--expect-status 401` is used, even a 200 response
will be reported as unhealthy. HTTP status codes 100–599 are accepted.

Without this option, the original 200–299 behavior remains. The command does
not follow redirects, read response bodies, or include query parameters in
diagnostic output. Timeouts and network failures are unhealthy regardless of
which status codes are expected.
