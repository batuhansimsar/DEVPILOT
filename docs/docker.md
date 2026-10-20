# Read-only Docker diagnostics

DevPilot's Docker integration is optional. No Docker daemon or Docker CLI is required for `devpilot doctor` or `devpilot test`.

```sh
devpilot docker                # check Docker availability and daemon connectivity
devpilot docker --json         # structured status
devpilot docker ps             # running containers (JSON metadata lines)
devpilot docker --json ps      # structured array of running containers
```

These commands only run `docker info --format {{.ServerVersion}}` and `docker ps --format {{json .}}`. They never start, stop, build, remove, or change anything. They do not invoke a shell or interpret a project-specific Dockerfile or Compose file.

The local Docker CLI must be installed and the current user must have permission to communicate with the Docker daemon. Commands time out after five seconds and cap retained output at 1 MiB. A nonzero exit code means Docker is missing, unreachable, or returned an error; pass `--json` to receive a structured report even on failure.

Docker container names and metadata may reveal internal service architecture. Review diagnostics before posting them publicly.
