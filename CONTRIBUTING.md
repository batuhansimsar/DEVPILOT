# Contributing

Use Go 1.23 or newer. Run `go test ./...`, `go vet ./...`, and `go build ./cmd/devpilot` before submitting a focused pull request. Please include regression tests for new detectors; diagnostic warnings must have observable evidence, a clear remedy and no secret values. Prefer small cross-platform dependencies and avoid executing workspace scripts by default. Open an issue for larger architectural changes.

All code contributions are licensed under the project's MIT license.
