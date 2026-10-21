# Read-only Dockerfile diagnostics

Use `devpilot dockerfile [--json] [path]` to inspect a project's root `Dockerfile` without a Docker installation, Docker daemon, package download, or AI subscription.

The command returns Docker build-stage inventory and findings with file/line evidence. Checks cover mutable base image tags (excluding `scratch` and known multi-stage aliases), curl/wget downloads piped into shells, `COPY . ...` without a `.dockerignore`, missing `FROM` instructions, remote `ADD` without an explicit checksum, and explicit root selection in the last stage.

```sh
devpilot dockerfile /path/to/project
devpilot dockerfile --json /path/to/project
```

Exit status: 0 if no warnings are found, 1 if warnings exist, and 2 on invalid input. JSON output is intended for CI integration.

**Limits:** This is static heuristic inspection, not a complete Dockerfile parser, an image-vulnerability audit, or proof that a container build is secure. Dynamic build arguments and advanced syntax may not be fully understood. Inputs must be regular files (symlinks rejected), content is capped at 1 MiB, and no Docker commands are executed.
