# DevPilot

**A local, zero-subscription developer project doctor.**

DevPilot is an early, working CLI prototype of an open-source Developer Control Center. It inspects unfamiliar projects **without executing their code** and helps you discover concrete next steps.

## Quick start

Requires Go 1.23+ to build (no external Go dependencies):

```sh
git clone https://github.com/batuhansimsar/DEVPILOT.git
cd DEVPILOT
go build -o devpilot ./cmd/devpilot
./devpilot doctor --path /path/to/project
./devpilot doctor --path /path/to/project --json
./devpilot test --path /path/to/project
```

On Windows use `go build -o devpilot.exe ./cmd/devpilot` and `devpilot.exe ...`.

For a one-off run: `go run ./cmd/devpilot doctor --path .`.

## What works in 0.1.0

- Detects Go, Node.js, Python, Rust, Java/Kotlin and .NET project manifests (root and shallow subprojects).
- Detects React, Next.js, Vue, Angular, Svelte, Express, Fastify, Vite and Nuxt when declared in Node package dependencies.
- Reports malformed `package.json`, conflicting package manager lockfiles, missing local toolchains, and environment templates needing review.
- Reads Git branch metadata **without executing Git hooks or external programs**.
- Discovers test commands for Go, Node, Rust, selected Python, Maven, Gradle and .NET test projects.
- Offers structured JSON output suitable for tools and CI.
- Runs a discovered test **only after explicit `--trust` approval** with a timeout, captured output cap and basic credential-pattern masking.

Example:

```sh
devpilot doctor --path ./your-repo
devpilot test --path ./your-repo
devpilot test --path ./your-repo --run go:. --trust --timeout 3m
```

**Security:** `doctor` only reads filenames, selected manifest contents and `.git/HEAD`. It does not read `.env` values, run package scripts, install dependencies, contact remote servers, or write into the inspected project. `test --trust` runs *untrusted project code* with your own permissions; use it only on projects you trust, ideally within an OS/container sandbox. The timeout kills the direct child process, but is not a complete process-tree sandbox. Do not run untrusted test code on a host with valuable credentials.

## Current limitations

This is an initial end-to-end CLI slice, not a finished desktop application. There is no web UI, Docker integration, dependency vulnerability scanning, automated repair, or interactive process manager yet. Git dirty-state detection is intentionally excluded from passive inspection. Analysis covers project files up to two levels of nesting and stops after 10,000 files; vendor/build directories and symlinks are skipped. A missing `.env` file is informational because variables can be supplied by other mechanisms. No claim of Windows/macOS support should be made until hosted CI confirms it.

## Development

```sh
go test ./...
go vet ./...
go build ./cmd/devpilot
gofmt -l cmd internal
```

See [architecture](docs/ARCHITECTURE.md), [contributing](CONTRIBUTING.md) and [security policy](SECURITY.md).
