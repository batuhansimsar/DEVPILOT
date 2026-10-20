# Architecture — milestone 0.1

The CLI entrypoint lives in `cmd/devpilot`; read-only manifest diagnostics live in `internal/doctor`. There is deliberately no local service, database, background daemon, plugin host, or AI requirement yet. The JSON output of `devpilot doctor --json` is a stable starting point for a future UI, though its schema is not frozen.

## Design decisions

- **Go standard library**: one compiled binary, cross-platform, no runtime dependency or third-party installation, low maintenance burden. Tradeoff: less convenient parsing of complex multi-language build manifests; this milestone avoids claiming complete architecture discovery.
- **Root-level inspection**: bounded work and lower traversal risk. Tradeoff: monorepos and nested app directories are not inspected yet.
- **Explicit workspace trust for tests**: untrusted scripts are never executed by `doctor`. `test` requires `--trust`. Tradeoff: a deliberate extra step even for familiar projects.
- **No web UI for the first vertical slice**: delivering a reliable CLI and JSON report before introducing a front-end toolchain avoids a mock dashboard. A later UI can consume JSON or a versioned local API.

## Trust boundaries

Manifest files and environment examples are untrusted. Inspection refuses symlinks and files over 1 MiB. `.env` values must never appear in findings. Repository-defined scripts require explicit user trust and use argument arrays rather than shell interpolation. Git HEAD is read without executing Git. Do not use DevPilot as a security sandbox: even trusted test commands can spawn child processes and access local credentials.

## Tree viewer addition

`internal/tree` provides a bounded, read-only traversal used by `devpilot tree`. It does not parse project source code or execute tools. Dependency/build directories are excluded, symlinks are represented but never followed, and depth/result limits prevent runaway output. The CLI supports text and JSON representations.
