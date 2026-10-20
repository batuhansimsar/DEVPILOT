# Docker Compose diagnostics

`devpilot doctor` now performs **read-only** root-level Docker setup checks. It recognizes `compose.yaml`, `compose.yml`, `docker-compose.yml`, `docker-compose.yaml`, and `Dockerfile` as regular files, but never reads Compose contents, follows symlinked Compose files, contacts the Docker daemon, or starts containers.

- `docker-compose-found` identifies actual Compose manifest filenames.
- `docker-compose-multiple-files` warns when multiple default Compose filenames coexist and might be unintentionally selected. Choose the intended file with `docker compose -f FILE ...` or remove obsolete configuration manually.
- `docker-cli-missing` warns when Docker configuration is present but the `docker` executable cannot be found on PATH. This does **not** diagnose whether the Docker daemon is running or accessible.
- `docker-cli-found` reports only Docker CLI availability, not engine health.
- `dockerignore-not-found` reminds Dockerfile authors to consider excluding local secrets and build outputs from the build context. Missing `.dockerignore` is informational, not proof of an existing vulnerability.

The checks intentionally do **not** validate YAML syntax, Compose profile semantics, Docker Desktop state, socket permissions, service health, or images. Those require separately designed trust and execution boundaries. No change is made to repository files or the user's environment.
