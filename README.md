# DevPilot

**A local, AI-optional control center for diagnosing developer projects.**

The first working milestone is a small Go CLI that inspects project manifests, detects language/framework and package-manager hints, checks for missing tools, discovers a test command, compares `.env` *names* (never values), and reads Git branch metadata. It does not execute repository code during inspection.

## Install / run

Requires Go 1.23+ for building. On macOS, Linux or Windows:

```sh
git clone https://github.com/batuhansimsar/DEVPILOT.git
cd DEVPILOT
go build -o devpilot ./cmd/devpilot
./devpilot doctor /path/to/your/project
./devpilot doctor --json /path/to/your/project
```

On Windows, run `devpilot.exe` instead of `./devpilot`.

## Commands

- `devpilot doctor [--json] [path]` — **read-only** root-level project diagnostics. Exit 0 for no warnings, 1 for warnings, 2 for invalid input.
- `devpilot test --trust [--timeout=2m] [path]` — run a discovered test command with a default 2-minute timeout (maximum 10 minutes). **Only use with repositories you trust.** Project test scripts can execute arbitrary code. There is no automatic testing in `doctor`.

Examples:

```sh
./devpilot doctor .
./devpilot doctor --json ../my-project
./devpilot test --trust ../my-trusted-go-project
```

## Supported detection

Manifest-driven detection of Go (`go.mod`), JavaScript/TypeScript (`package.json`), Python (`pyproject.toml`, `requirements.txt`, `pytest.ini`), Rust (`Cargo.toml`), and .NET (`*.csproj`, `*.fsproj`, `*.vbproj`, `*.sln`, `*.slnx`) at the project root. JS frameworks detected from `package.json` dependencies include React, Next.js, Vue, Angular, Express and Vite. Test commands are discovered for Go, Cargo, pytest (if configured), JavaScript projects with a test script, and .NET when one unambiguous project or solution target exists. .NET detection reads filenames only and does not execute project code.

`.env.example`, `.env.sample` and `.env.template` are compared with local `.env` on **variable names only**; values are never included in the report. Missing `.env` keys are informational because variables can be supplied outside the file.

## Safety and limitations

- Project content is untrusted; inspection reads a limited set of root-level files, refuses symlinked manifests, and limits inspected file size to 1 MiB.
- `doctor` does not run dependency installation, project test scripts, shells, repair commands, or AI agents.
- `test --trust` grants code execution to the inspected workspace. Test output may include secrets exposed by those scripts; never run it on untrusted projects or with sensitive credentials.
- `.env` checks do not validate runtime environment variables or whether values are valid.
- Git inspection reads `.git/HEAD` only; it deliberately does not invoke Git or inspect tracked/untracked changes in untrusted workspaces. No recursive architecture scan, GUI, or container integration is implemented yet.
- A missing `go`, `python`, `cargo` or JS package manager on PATH is reported as a warning when needed.

## Development

```sh
go test ./...
go vet ./...
gofmt -w cmd internal
```

See [architecture](docs/architecture.md), [contribution guide](CONTRIBUTING.md), and [security policy](SECURITY.md).
