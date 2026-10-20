# DevPilot

**A local, AI-optional developer control center.** The first functional milestone is a dependency-free Go CLI that explains unfamiliar project roots and discovers how to test them.

> Early development: the CLI inspects top-level manifests only. It does not yet provide a desktop/web UI, architecture graphs, Docker health monitoring, or automatic repairs.

## Quick start

Requires Go 1.22 or newer to build. No account, API key, or paid AI service is required.

```sh
git clone https://github.com/batuhansimsar/DEVPILOT.git
cd DEVPILOT
go build -o devpilot ./cmd/devpilot
./devpilot doctor .
./devpilot doctor --json /path/to/project
```

On Windows, use `go build -o devpilot.exe ./cmd/devpilot` and `devpilot.exe doctor .`.

## Doctor: passive checks

```sh
devpilot doctor [--json] [workspace]
```

- Detects top-level Go, Node.js, Rust, Python, Maven, Gradle, and .NET manifests.
- Recognizes common JavaScript frameworks and package managers.
- Discovers supported test commands; checks whether some toolchains are on `PATH`.
- Identifies multiple Node lockfiles and malformed `package.json` files.
- Reports Git/Compose presence, but does **not** execute them.
- Counts `.env.example` variable names without reporting values.
- Produces actionable findings with severities and JSON output.

Findings describe only what can be observed; absence of a `node_modules` directory does not prove dependencies are broken. `doctor` does not run code, install packages, access the network, read `.env`, or traverse source trees. Exit status: `0` for successful inspection, `1` for a diagnostic error or invalid workspace, `2` for invalid arguments.

## Execute tests (opt-in)

```sh
devpilot test --trust /path/to/trusted/project
devpilot test --trust --timeout=2m .
```

`--trust` is mandatory because package scripts, build tools, and test runners can execute arbitrary repository code. DevPilot executes a detected test command as a direct subprocess, not through a shell, with a default 90-second timeout. It runs the first detected test command only; inspect `doctor` output before execution. Logs may contain secrets emitted by your own tests. Do **not** run tests against untrusted repositories. No sandbox is provided.

## Development

```sh
go test ./...
go vet ./...
go build ./cmd/devpilot
```

The code intentionally uses Go's standard library only. This keeps the initial installation small and avoids premature services or frontend dependencies. Future work should add precise detection tests and improve cross-platform behavior before introducing a UI.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). Changes should go through a focused pull request and pass tests. See [LICENSE](LICENSE).
