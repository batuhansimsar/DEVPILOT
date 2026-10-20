# DevPilot Environment Audit (first functional tool)

A zero-dependency, read-only Go CLI for checking whether documented local environment variable **names** have configuration evidence. It does not require an AI provider, access credentials, Docker, or a running app.

## Run

Requires Go 1.21 or newer. From this directory:

```sh
go run ./cmd/devpilot-env --path /path/to/project
# Machine-readable report (values are excluded):
go run ./cmd/devpilot-env --path /path/to/project --json
# Fail with exit code 1 if any documented variable is unconfigured:
go run ./cmd/devpilot-env --path /path/to/project --strict
# Compile a single executable:
go build -o devpilot-env ./cmd/devpilot-env
```

For a checked-out DevPilot repository, start with `cd tools/envcheck`. The command does **not** execute project scripts, install dependencies, modify files, or invoke a shell.

## What is detected

At the selected project's top level, the tool reads regular (non-symlink) `.env.example`, `.env.sample`, `.env.template`, and `.env.<name>.example` / `.sample` / `.template` files. It also looks for nonempty values in a regular `.env` file and in the current process environment.

Each documented variable gets one of these statuses:

- `in_process`: a nonempty value exists in the **current process** environment.
- `in_dotenv`: a nonempty value appears in `.env`, but no nonempty process value was found.
- `unconfigured`: neither source contains a nonempty value.

**Important:** `in_dotenv` does not prove the application will load `.env`. Conversely, `unconfigured` is not proof of a broken application: variables may be optional, injected by external tooling, or sourced from files not inspected. By default this is informational and exits 0; use `--strict` to enforce your own policy.

No variable *values* are recorded in the structured report or printed. Variable names and filenames are shown. It does not inspect nested workspaces, `.env.local`, secrets managers, runtime config, or template syntax other than `KEY=value` and `export KEY=value`. It does not determine whether sample values are actually valid credentials. Symlinked files are ignored; configuration files larger than 1 MiB cause a clear error.

## Verification

```sh
cd tools/envcheck
go test ./...
go vet ./...
```

The long-term CLI can reuse `internal/envcheck` after this isolated functionality is reviewed. This deliberately avoids duplicating any concurrently developed `devpilot doctor` implementation.
