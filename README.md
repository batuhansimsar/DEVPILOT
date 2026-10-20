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
devpilot doctor --path /path/to/project
devpilot git --path /path/to/project
devpilot docker
devpilot check localhost 5432
devpilot test --path /path/to/project           # discovery only
# Review the proposed command first; test scripts execute project code:
devpilot test --path /path/to/trusted/project --yes --timeout 120
# JSON outputs for scripts and integrations:
devpilot doctor --path /path/to/project --json
```

| Command | Behavior |
| --- | --- |
| `workspaces` | Discovers nested Python, Node.js, Go, Rust, Java, .NET, Ruby and PHP projects without following symlinks or reading file contents. | 
| `analyze` | Detects Node.js, Python, .NET, Go, Rust, Java and Docker markers; counts source files by language; lists manifests and npm script names. |
| `doctor` | Checks whether relevant language runtimes and CLI tools are on your `PATH`, and reports malformed package manifests. |
| `git` | Executes read-only `git status` with no shell. |
| `docker` | Executes read-only `docker ps`; reports running containers. |
| `check` | Attempts a TCP connection to a supplied hostname and port. |
| `test` | Discovers test commands for supported ecosystems. Dry-run by default; only `--yes` executes code, with per-command timeouts. |

## Security and limits

DevPilot is designed to **inspect before acting**. Analysis skips symlinked files and folders, dependency/build directories, and caps scans at 10,000 files / 12 directory levels. It never reads `.env` contents or executes project scripts during `doctor` or `analyze`. External tools such as Git and Docker are invoked with argument arrays, **not shell interpolation**. CLI stdout/stderr may contain sensitive project data; do not publish `--json` output blindly. `test --yes` runs untrusted repository code and should only be used with projects you trust. The `check` command opens a network connection only to the host explicitly supplied. No telemetry is collected.

The language detector targets root-level manifests; this early release does not recursively detect every monorepo workspace or replace CI/security scanners. Docker must be installed and running to use `docker`.

## Development

```bash
python -m pip install .
python -m unittest discover -s tests -v
```

Contributions are welcome. Please add regression tests for bug fixes. For security reports, do not publish credentials, exploit data, or private logs in public issues; reach out to the maintainers privately first.

Licensed under the MIT License.

JavaScript diagnostics flag multiple lockfiles (`pnpm-lock.yaml`, `yarn.lock`, Bun, npm lock/shrinkwrap) with a warning; `doctor` does not execute package scripts.
