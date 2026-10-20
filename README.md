# DevPilot

**Open-source developer control center — initial CLI milestone.**

DevPilot helps engineers inspect unfamiliar repositories, identify frameworks, discover test commands, review local Git state and spot configuration problems. It runs locally without a paid AI subscription, server or account.

> Status: early alpha. The current product is a working **CLI**, not a desktop or web UI. Docker checks, service monitoring, and AI integrations are future milestones.

## Get started

Requires **Go 1.23+**. Clone this repository and run:

```sh
go run ./cmd/devpilot doctor --path .
```

Build a local executable:

```sh
go build -o devpilot ./cmd/devpilot
./devpilot doctor --path /path/to/your/project
./devpilot doctor --json
```

On Windows, build with `go build -o devpilot.exe ./cmd/devpilot` and run `devpilot.exe doctor`.

## What doctor does

- Detects Go, Node.js, React, Next.js, Vue, Angular, Vite, Express, TypeScript, Vitest, Jest, Python, Rust, Maven, Gradle, .NET and Docker Compose by scanning relevant manifest filenames and (for JavaScript) declared dependencies.
- Finds `go test ./...` and `npm test` commands where supported, without executing them by default.
- Reports invalid `package.json` files, conflicting JavaScript lockfiles, environment template presence, Git changes and an exact `.env` accidentally tracked at the root.
- Outputs human-readable findings or versioned JSON (`--json`) with evidence and suggested remedies.

The analyzer only looks at the repository root and two subdirectory levels. It skips symlinks, hidden directories and build/vendor caches. Detection is evidence-based and intentionally not exhaustive.

### Opt-in test execution

```sh
./devpilot doctor --path ./examples/go-sample --run-tests --trust-workspace --timeout 30s
```

**Security:** enabling tests executes project-controlled commands and is **not sandboxed**. Only use this option on repositories you trust. No shell interpolation is used, but package scripts can run arbitrary commands. Output is truncated and redacted best-effort; review before sharing.

## Development

```sh
go test ./...
go vet ./...
go build ./cmd/devpilot
```

See [architecture](docs/architecture.md), [contribution guide](CONTRIBUTING.md) and [security policy](SECURITY.md). CI tests the CLI on Linux, macOS, and Windows; support is not claimed until those runs pass.

## License

MIT, see [LICENSE](LICENSE).
