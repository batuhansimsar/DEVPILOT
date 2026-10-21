# DevPilot Runbook Discovery

A working, AI-free, read-only command-discovery utility for unfamiliar repositories. This is a standalone component for later integration with DevPilot doctor.

Requires Go 1.22 or later. Run from this directory:

    go run . -root /path/to/project
    go run . -root /path/to/project -json
    go test ./...
    go vet ./...

It discovers candidate run, test, build, lint and check commands from package.json scripts, go.mod, Cargo.toml and Makefile. JavaScript package-manager detection uses the packageManager field or recognized lockfiles.

**Safety:** No discovered command is executed. All results are unverified suggestions, not proof a build or test succeeds. Malformed or symlinked manifests are rejected. Scripts may execute unsafe third-party code, so review before running them.

JSON fields: status (discovered or no-manifest), candidates (command, purpose, evidence, verified=false), and optional warnings. Exit 0 = inspection succeeded; exit 2 = inspection or invocation failed.

It has a separate Go module to avoid conflicts with simultaneous DevPilot bootstrap development. Future work can integrate this tool with the main CLI.
