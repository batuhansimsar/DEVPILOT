# Read-only dashboard

DevPilot offers a local web view of the existing doctor report. No AI, Node runtime, or remote server is required.

Usage:

    go build -o devpilot ./cmd/devpilot
    ./devpilot ui --port=0 /path/to/project

The command prints an http://127.0.0.1 URL; open that URL in a browser. Port 0 requests an available loopback port. The workspace path is fixed when the process starts. Ctrl+C terminates the process.

The dashboard displays languages, frameworks, package-manager hints, diagnostics, and discovered test commands from doctor.Inspect. It never triggers dependency installation, tests, Git commands, or other project scripts. Refresh the page to run a new read-only scan. The /api/report endpoint returns the same JSON report as the doctor CLI.

Security boundaries: IPv4 loopback-only listener, Host header validation, GET/HEAD-only endpoints, restrictive CSP, escaped HTML template data, no state-changing endpoints, no analytics or network calls to external services. Local browser extensions and other programs on the same machine can still read the dashboard; this is not an authentication boundary. Do not forward the port or proxy it to the public Internet.

This initial version uses Go HTML templates so the first UI has zero additional dependencies and is available offline. A React/TypeScript dashboard can replace the presentation later without changing the diagnostic engine.
