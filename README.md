# DevPilot

**DevPilot is a local-first, cross-platform Developer Control Center CLI.** Inspect unfamiliar repositories, discover tool requirements, see Git and Docker status, check TCP services, and identify test commands before deciding to execute them. No API key or account required.

> Early release (v0.1.0). This is a working CLI foundation, not yet a desktop dashboard or autonomous agent.

## Install

Requires Python 3.10+ on Windows, macOS, or Linux.

```bash
git clone https://github.com/batuhansimsar/DEVPILOT.git
cd DEVPILOT
python -m pip install .
devpilot --help
```

For local source development without installing: `PYTHONPATH=src python -m devpilot --help` (macOS/Linux), or use `set PYTHONPATH=src` on Windows CMD.

## Commands

```bash
devpilot analyze --path /path/to/project
devpilot workspaces --path /path/to/monorepo --json
devpilot env --path /path/to/project --json
# Tune bounded discovery for small or very large workspaces:
devpilot workspaces --path /path/to/monorepo --max-depth 3 --max-directories 1000 --json
devpilot doctor --path /path/to/project
devpilot git --path /path/to/project
devpilot git --path /path/to/project --fail-on-dirty --json  # CI-friendly dirty-tree gate
devpilot audit --path /path/to/project       # filename-only scan of Git-tracked potential secrets
devpilot docker
devpilot check localhost 5432
devpilot check example.com 443 --tls --json  # verify TLS certificate and hostname
# HTTP HEAD health check (redirects are not followed):
devpilot http http://localhost:8080/health --json
devpilot test --path /path/to/project           # discovery only
devpilot test --path /path/to/project --ecosystem go  # select only Go tests
# Review the proposed command first; test scripts execute project code:
devpilot test --path /path/to/trusted/project --yes --timeout 120
# JSON outputs for scripts and integrations:
devpilot doctor --path /path/to/project --json
```

| Command | Behavior |
| --- | --- |
| `env` | Compares environment variable names against an `.env` template without printing secret values. Missing keys return exit status 1; no local `.env` is advisory. |
| `workspaces` | Discovers nested Python, Node.js, Go, Rust, Java, .NET, Ruby, PHP and Docker/Compose projects without following symlinks or reading file contents. | 
| `analyze` | Detects Node.js, Python, .NET, Go, Rust, Java and Docker markers; counts source files by language; lists manifests and npm script names. |
| `doctor` | Checks whether relevant language runtimes and CLI tools are on your `PATH`, and reports malformed package manifests. |
| `git` | Executes read-only Git porcelain status with no shell; JSON includes `dirty` (`true`, `false`, or `null` on Git failure). `--fail-on-dirty` exits nonzero for changed files. |
| `audit` | Warns about Git-tracked `.env`, private keys, and credential-like filenames without opening their contents. |
| `docker` | Executes read-only `docker ps`; reports running containers. |
| `check` | Attempts a TCP connection to a supplied hostname and port. |
| `http` | Sends a bounded HTTP HEAD request without following redirects or reading the response body. Only HTTP 2xx is considered healthy; 3xx is reachable but unhealthy. Query strings are omitted from the displayed URL. |
| `test` | Discovers test commands for supported ecosystems. Dry-run by default; `--ecosystem node|python|go|rust|dotnet|java` limits discovery and execution to one ecosystem. Only `--yes` executes code, with per-command timeouts. |

## Security and limits

`devpilot doctor` warns if Git tracks potentially sensitive `.env` files (including nested `.env.production` or `.env.local`). Template filenames such as `.env.example` and `.env.sample` are excluded. This check inspects Git's index only; it never reads environment-file contents.

DevPilot is designed to **inspect before acting**. Analysis skips symlinked files and folders, dependency/build directories, and caps scans at 10,000 files / 12 directory levels. It never prints `.env` values or executes project scripts during `doctor` or `analyze`. External tools such as Git and Docker are invoked with argument arrays, **not shell interpolation**. Git status disables repository-configured filesystem-monitor hooks and optional index writes, avoiding unexpected helper execution during inspection. CLI stdout/stderr may contain sensitive project data; do not publish `--json` output blindly. `test --yes` runs untrusted repository code and should only be used with projects you trust. The `check` command opens a network connection only to the host explicitly supplied. No telemetry is collected.

The language detector targets root-level manifests; this early release does not recursively detect every monorepo workspace or replace CI/security scanners. Docker must be installed and running to use `docker`.

The explicit `env` command performs the same variable-name comparison and exits unsuccessfully if expected names are missing. The Python `doctor` command also compares variable **names only** from root-level `.env.example`, `.env.sample`, or `.env.template` against `.env` (when present). No values are printed; missing local keys are informational because variables may be provided externally. Symlinked or oversized environment files are not inspected (256 KiB limit).

## Development

```bash
python -m pip install .
python -m unittest discover -s tests -v
```

Contributions are welcome. Please add regression tests for bug fixes. For security reports, do not publish credentials, exploit data, or private logs in public issues; reach out to the maintainers privately first.

Licensed under the MIT License.

JavaScript diagnostics flag multiple lockfiles (`pnpm-lock.yaml`, `yarn.lock`, Bun, npm lock/shrinkwrap) with a warning; `doctor` does not execute package scripts.


### HTTP health checks

Probe an explicitly supplied HTTP endpoint without reading the response body or following redirects:

```bash
devpilot http http://localhost:8080/health --json
```

The command defaults to HEAD, reports HTTP status and latency, and treats HTTP 3xx/4xx/5xx as unhealthy unless explicitly allowed with `--expect-status`. For endpoints that reject HEAD, use `devpilot http http://localhost:8080/health --method GET --json`. GET can have application side effects, so it is opt-in. DevPilot does not read GET response bodies or follow redirects. JSON output includes the selected `method`. Credentials in URLs are rejected; query parameters are omitted from diagnostics. Use `--timeout 5` to adjust the deadline (0.1–30 seconds).

## Dependency inventory

`devpilot deps --path /path/to/repo` reports dependency names in Node.js `package.json`, Python `requirements*.txt`, Go `go.mod`, Rust `Cargo.toml`, and .NET project files. Use `--json` for machine-readable output. This is a bounded, read-only scan that does not execute project code or access the network. Version specifications and dependency URLs are deliberately omitted to avoid exposing credentials. This is **not** a vulnerability audit.

## TLS certificate expiry warnings

Use `devpilot check example.com 443 --tls --json` to verify a service certificate and inspect `expires_at`. When the certificate has an expiration date, the JSON response also includes `expires_in_days` (full days remaining, floored at zero) and `expires_soon` (true when expiry is within 30 days). These are renewal hints; exit status still reflects TLS verification rather than renewal urgency. No certificate data is stored or sent to third parties.
