# TCP connectivity checks (Go CLI)

Use `devpilot check` to test whether a TCP connection can be opened to an explicitly supplied host and port. The check sends no application data, runs no repository scripts, and does not require elevated permissions.

~~~bash
go run ./cmd/devpilot check --timeout=2s localhost 5432
go run ./cmd/devpilot check --json 127.0.0.1 8080
~~~

Options must appear before the host and port. The default timeout is 3 seconds; valid values are 100 milliseconds through 30 seconds. IPv4, IPv6, and DNS names are supported.

Exit codes: `0` means the TCP connection succeeded, `1` means it failed or timed out, and `2` means invalid arguments or a JSON output error. JSON includes `host`, `port`, `reachable`, `latency_ms` (elapsed DNS/dial time on success or failure), and optionally a connection error. Human-readable output includes the rounded duration in milliseconds. Connection errors use fixed, privacy-preserving categories rather than raw resolver or OS diagnostics. The supplied endpoint is still included in output, so review it before sharing.

A successful connection does **not** prove application readiness, credentials, TLS correctness, or protocol health. Failed checks may be caused by DNS, firewalls, routing, or a closed port. This command makes a network connection to the supplied destination; use it only for hosts you are authorized to probe.
