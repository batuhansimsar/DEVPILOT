# DevPilot — Local Developer Control Center

An open-source project doctor that identifies project structure, development prerequisites, potential configuration problems and safe test commands — without a paid AI subscription.

**Stage: functional CLI bootstrap.** The UI, Docker integrations, performance analyzer and automated repair features in the long-term roadmap are **not yet implemented**.

## Install from source

Requires Go 1.23 or newer.

```sh
git clone https://github.com/batuhansimsar/DEVPILOT.git
cd DEVPILOT
go build -o devpilot ./cmd/devpilot
```

On Windows, use `go build -o devpilot.exe ./cmd/devpilot`. Until the code is merged, check out the bootstrap PR branch before building.

## One-command project diagnostics

```sh
./devpilot doctor /path/to/project
./devpilot doctor --json /path/to/project
```

With no arguments, `devpilot` runs `doctor` on the current directory. The doctor:

- Detects Go, JavaScript/TypeScript, Python, Rust, and root-level C#/.NET projects.
- Recognizes React, Next.js, Vue, Angular, Express, Vite, Svelte, and NestJS dependencies.
- Detects npm, pnpm, yarn and bun lockfiles and flags conflicting package managers.
- Checks available local toolchains without installing anything.
- Discovers supported test commands without executing them.
- Checks whether key names in `.env.example`, `.env.sample` or `.env.template` have local entries. It never prints secret values. Missing keys may be optional.
- Summarizes Git tracked-file modifications, without exposing file names or inspecting untracked files.

Every finding has evidence and a suggested next step; a detected manifest is not evidence that the application successfully runs.

## Opt-in test execution

```sh
./devpilot test --trust /path/to/reviewed-project
./devpilot test --trust --runner go --timeout 3m /path/to/reviewed-project
```

Without `--trust`, no test command is executed. Select a runner using `--runner go|node|python|rust|dotnet` when more than one is detected. Test scripts can execute arbitrary project code with your user permissions; review the repository **before** using `--trust`.

## Development

```sh
go test ./...
go vet ./...
go build ./cmd/devpilot
```

This milestone is Go standard-library-only and requires no cloud backend, account, or AI service. Diagnostics do not intentionally make network calls. Manifests are read only at the workspace root; symlinked manifests are skipped and individual file reads are limited to 1 MiB.

Runtime compatibility across Linux, macOS and Windows will be established through CI, not assumed from cross-compilation alone.

See [architecture](docs/ARCHITECTURE.md), [security policy](SECURITY.md), and [contributing](CONTRIBUTING.md).

## Roadmap (not implemented yet)

Monorepo analyzers, richer framework diagnostics, Docker Compose analysis, accessible desktop/web UI, service monitoring and optional AI agent integrations — only after the CLI core has reliable tests and usable reports.

## License

MIT, see [LICENSE](LICENSE).
