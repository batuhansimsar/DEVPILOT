# DevPilot

DevPilot is an open-source, local-first developer project inspector. Its first milestone is a **working, zero-third-party-dependency Go CLI**. It never requires an AI account.

## Install and run

Requires Go 1.22 or newer. From the repository root:

```sh
go build -o devpilot ./cmd/devpilot
./devpilot doctor --path /path/to/project
./devpilot doctor --path /path/to/project --json
```

On Windows build with `go build -o devpilot.exe ./cmd/devpilot`.

To run tests in a **trusted** workspace only:

```sh
./devpilot test --path /path/to/project --trust --timeout 2m
./devpilot test --path /path/to/project --runner go --trust
```

`doctor` examines root-level project manifests and file names without running project commands. It recognizes Go, JavaScript/TypeScript, Python, Rust, and .NET; detects some frameworks, JavaScript lockfile conflicts, missing CLI tools, available test runners, Git metadata, and environment variable *names* declared in `.env.example`. Warnings return exit code 1; successful inspections return 0; invalid CLI usage returns 2. The JSON option is suitable for further tooling.

`test` deliberately refuses execution unless `--trust` is supplied because even standard test scripts can execute arbitrary code. It invokes tools without a shell, gives commands a configurable timeout (15 minutes maximum), and requires an explicit `--runner` when several runners are discovered. **Review repository contents and scripts before enabling trust.**

## Limitations

- Detection is currently root-level and heuristic, not a full dependency or architecture audit.
- Environment inspection checks the current process environment, not `.env` file values; absent exports are informational and may be provided by other mechanisms.
- `doctor` does not execute Git, install dependencies, or evaluate arbitrary configuration files.
- CI currently runs on Linux; cross-platform compatibility has not yet been verified in CI.
- Web/desktop UI, Docker diagnostics, and persistent history are future milestones, not implemented features.

## Development

```sh
go fmt ./...
go vet ./...
go test ./...
go build ./cmd/devpilot
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).
