# Go CLI: recursive repository analysis

The native Go CLI has a read-only `analyze` command for inventorying nested
projects and GitHub Actions, GitLab CI, Azure Pipelines, Jenkins, CircleCI, Bitbucket Pipelines, Travis CI, Drone CI, and Buildkite configuration files.

```bash
go run ./cmd/devpilot analyze .
go run ./cmd/devpilot analyze --json /path/to/monorepo
```

The output includes source-language counts, nested manifest paths, CI definitions,
the number of discovered files, and whether the scan stopped at its 20,000-file
limit. Files are counted, not read; symlinks and generated/dependency directories
are skipped. There is no project execution, Docker access, Git invocation, or
network access in this command.

A nonzero exit status indicates an incomplete scan or invalid path. JSON is
intended for automation. This inventory is based on filename conventions and
is not a dependency or security audit.

Run checks: `go test ./...`, `go vet ./...`, and `gofmt -l cmd internal`.

## Docker configuration discovery

`analyze` reports Dockerfiles (including named variants such as `Dockerfile.dev`)
and Docker Compose manifests (`compose.yml`, `compose.yaml`,
`docker-compose.yml`, `docker-compose.yaml` and named variants like
`docker-compose.override.yml`) among the sorted manifest paths. Matching is
case-insensitive. These are filename conventions only: analysis neither reads
Compose values nor invokes Docker, and symlinks remain excluded.

The `containers` field inventories Dockerfiles, Podman Containerfiles, and Docker
Compose YAML files, including nested service directories. It stores relative
paths only; files are never opened or executed. Backups and dependency/build
trees are excluded from this list.
