# DevPilot

**DevPilot is a local-first open-source developer project diagnostic CLI.** Understand a repository before running it. No paid AI service, sign-in, Docker daemon, database, or network connection required.

> Status: v0.1.0-dev (working CLI). No desktop/web UI, automatic repairs, or official release binaries yet.

## Quick start

Requirements: Go 1.22+ for building.

```sh
git clone https://github.com/batuhansimsar/DEVPILOT.git
cd DEVPILOT
go build -o devpilot ./cmd/devpilot
./devpilot doctor .
./devpilot doctor --json /path/to/repository
./devpilot test --list /path/to/repository
```

On Windows, use `go build -o devpilot.exe ./cmd/devpilot` and `devpilot.exe doctor .`.

## Real functionality

`devpilot doctor` performs read-only bounded scans of Go, Node, Python, Rust, .NET, and Docker Compose manifests. It recognizes selected JS frameworks and test scripts, conflicting package-manager lockfiles, missing executables, malformed package JSON, local Git tracked changes, and environment-template key names without exposing values. Use `--json` for machine-readable findings, `--strict` to fail on error-level findings. Results explain their evidence and recommended next actions.

`devpilot test --list` lists discovered commands without running them. To execute commands **only for a repository you trust**:

```sh
./devpilot test --run --trust-workspace --timeout=120s .
```

**Safety:** Test tools and package scripts can run arbitrary code. `--trust-workspace` is not an isolation boundary. By default DevPilot never invokes workspace scripts and never fixes issues or changes project files.

## Development

```sh
go fmt ./...
go vet ./...
go test ./...
go test -race ./...
```

See `docs/architecture.md`, `CONTRIBUTING.md` and `SECURITY.md`.

## Roadmap

Improve detection accuracy and fixtures first; then add Docker Compose diagnostics and an optional local web UI. Avoid AI dependencies for basic diagnosis.

## License

MIT (see LICENSE).
