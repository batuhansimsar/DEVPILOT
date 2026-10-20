# Architecture — ADR 0001

## Technology

The first vertical slice is a **single Go 1.22 CLI** built with the standard library. This allows a small runtime footprint, single executable, cross-compilation, test timeouts, and straightforward maintainability.

Trade-offs: binaries are bigger than small scripts and not all project manifests can be interpreted yet. Adding React, Wails, SQLite or an AI runtime before the CLI works would increase upkeep without immediate diagnostic value.

## Flow

CLI parses arguments -> bounded read-only project scan -> evidence-backed `Report` -> terminal or JSON. Optional test execution is separately gated by `--run --trust-workspace`.

## Security

Repository contents are untrusted data. Manifest reads are limited to 1 MiB; scan depth is 5; the scan stops after 12,000 files. Symbolic links and known dependency/build folders are ignored. Actual `.env` values are never read, only variable names from templates. Git status is read-only and bounded to four seconds. Test commands run through Go's exec API, not a DevPilot-created shell, but npm and similar tools can invoke scripts internally. Explicit trust is required.

## Unimplemented

Desktop/web UI, secret storage, robust process-tree teardown, Docker services, full dependency graphs, vulnerability scanning, automatic repairs, persistent history, and official release packages require further work.
