# Contributing

Contributions should address a reproducible developer problem and include regression tests. Open an issue first for larger features. Work in a feature branch, run `go test ./...`, `go vet ./...`, and `go build ./cmd/devpilot`, then open a focused pull request. Do not push directly to `main`. Treat inspected project files as untrusted input and keep diagnostics read-only by default. Do not add dependency-heavy features unless their value and maintenance impact are documented.
