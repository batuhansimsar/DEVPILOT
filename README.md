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

Manifest-driven detection of Go (`go.mod`), JavaScript/TypeScript (`package.json`), Python (`pyproject.toml`, `requirements.txt`, `pytest.ini`), Rust (`Cargo.toml`), and top-level C# (`*.csproj`). JS frameworks detected from `package.json` dependencies include React, Next.js, Vue, Angular, Express and Vite. Test commands are discovered for Go, Cargo, pytest (if configured), and JavaScript projects with a test script.

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

## Project tree outline

```sh
./devpilot tree /path/to/project
./devpilot tree --depth=4 --json /path/to/project
```

`devpilot tree` produces a bounded, read-only directory outline; it never opens project file contents or runs scripts. It shows directories, regular files and symbolic link names **without following directory symlinks**. Build/dependency directories (including `.git`, `node_modules`, `vendor`, `dist` and `target`) are excluded. Depth must be between 1 and 6 (default 3), and output is capped at 4,000 entries with an explicit truncated flag. JSON output makes the structure available to other tools.
