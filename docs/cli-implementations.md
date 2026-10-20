# Go CLI and Python CLI coexistence

DevPilot currently has **two distinct command-line entry points**:

| Implementation | Location | Run |
| --- | --- | --- |
| Python (primary) | `src/devpilot/` | `python -m pip install .` then `devpilot --help` |
| Go (inspector) | `cmd/devpilot/` | `go run ./cmd/devpilot doctor --json .` |

The Python CLI offers project analysis, doctor checks, Git/Docker inspection, TCP checks, and an opt-in test runner. The Go CLI provides a conservative, **read-only** doctor with manifest-based language/framework detection, `.env` key-name comparison, and a separate trust-gated test runner.

The flag sets are **not interchangeable**. For example:

- Python: `devpilot doctor --path . --json`, `devpilot test --yes --path .`
- Go: `go run ./cmd/devpilot doctor --json .`, `go run ./cmd/devpilot test --trust .`

Run the Go CLI through `go run` or a binary with an explicit name, so an installed Python `devpilot` command is not accidentally shadowed.

Go test/build checks run independently on Linux, macOS, and Windows in [Go CLI CI](../.github/workflows/go-ci.yml). Python tests run through the separate CI workflow.

This split is transitional: functionality is preserved while maintainers decide how to consolidate a single public CLI. Do not assume the two implementations behave identically, and do not remove one without a migration and regression tests.
