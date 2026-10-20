# Architecture

The first milestone deliberately has no runtime dependencies other than Go's standard library:

- `cmd/devpilot`: CLI and human/JSON output.
- `internal/doctor`: bounded, read-only workspace and manifest scanning; deterministic diagnostics and test discovery.
- `internal/runner`: explicitly authorized discovered test execution using argument arrays (not a shell), bounded output and timeouts.

Go was selected for a single distributable executable, portable process APIs and low operational complexity. It increases contributor familiarity requirements compared with TypeScript, but avoids forcing Node into users' projects. React/TypeScript and optional desktop packaging can be introduced later when a real UI workload is defined and measured.

## Trust boundaries

Directory entries, manifest contents, `.git` pointers and test output are untrusted. Passive analysis skips symlinked entries, bounds reads and limits depth/count. Manifests only contribute known test entry points; user-specified shell commands are not accepted. `test --trust` grants the selected project command the invoking user's full privileges and should not be confused with sandboxing.
