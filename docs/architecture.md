# Architecture (first milestone)

DevPilot currently uses one Go executable, without a daemon, paid AI provider, or database. `cmd/devpilot` parses CLI arguments, and `internal/doctor` discovers manifests, emits evidence-backed findings, and executes discovered tests only after explicit trust acknowledgment.

## Constraints and trade-offs

- **Go:** single-binary distribution, mature process and filesystem APIs, cross-platform support. Trade-off: UI features will need a separate frontend if/when validated by users.
- **No React or SQLite yet:** a GUI and local state were deferred to avoid shipping placeholders; JSON output provides a stable interface for future UI consumers. No collected data is stored or sent over a network.
- **Shallow discovery:** inspect the root and at most two subdirectory levels, skipping symlinks, vendor/build directories and hidden folders; this prevents expensive traversals and reduces exposure to malicious trees. Deeper monorepos are not yet supported.
- **No auto-remediation:** findings include actionable next steps but never modify the workspace.
- **Restricted command execution:** Git inspection runs read-only Git commands; tests are opt-in via both `--run-tests` and `--trust-workspace`. No shell is used. Test execution is **not** a sandbox; only run against trusted code.

## Report schema v1

`devpilot doctor --json` emits `schema_version`, `workspace`, `detections`, `findings`, `test_commands`, and optional `test_results`. Findings include stable `code` and `severity`, plus evidence and remedy. Consumers should tolerate new fields and new finding codes.

## Future work

- Detect appropriate package managers, Python test tools and .NET tests more accurately.
- Detect broken environment dependencies using observed tool availability, not inferred failures.
- Structured Docker and CI checks; optional local dashboard once the CLI workflow is reliable.
- Workspace trust allowlists, subprocess tree termination, and improved log redaction prior to broader integrations.
