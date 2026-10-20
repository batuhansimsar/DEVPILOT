# Read-only local dashboard

After the Doctor CLI contribution is available, build the web companion:

    go build -o devpilot-web ./cmd/devpilot-web
    ./devpilot-web -path /path/to/project

Open http://127.0.0.1:3847 in a browser. The -listen flag permits loopback addresses only.

The dashboard uses doctor.Inspect, the same engine as the CLI. /api/doctor returns the actual JSON report. The interface shows languages, frameworks, discovered test commands, evidence-based findings, and remediation steps. Rescan reloads diagnostics on demand.

## Engineering rationale

Static HTML, CSS and JavaScript are embedded into a Go binary. No Node runtime or paid AI subscription is required. React may be preferable for advanced workflows later, but is not justified for this read-only interface.

## Security boundaries

The server defaults to 127.0.0.1 and refuses non-loopback bindings and untrusted Host headers. The UI does not load external scripts, enable CORS, execute test scripts, or allow file changes. Content Security Policy and textContent-based rendering prevent untrusted repository text from being interpreted as HTML.

This contribution is stacked on the foundational Doctor CLI pull request (#2) so the implementation can be reviewed independently. Merge that PR first, then retarget this PR to main if needed.
