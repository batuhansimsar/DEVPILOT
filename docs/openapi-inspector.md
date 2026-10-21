# Offline OpenAPI Inspector

`devpilot-openapi` is an independent, zero-dependency Go command that lists API endpoints from local **OpenAPI 3.x** and **Swagger 2.0 JSON** files. This module is intentionally isolated from the concurrently developed `devpilot doctor` CLI, so it can be integrated later without overwriting other contributors' work.

## Run

Requires Go 1.22+. From this repository:

```sh
cd tools/openapi-inspect
go run . /path/to/project
go run . --json /path/to/project
go run . --strict /path/to/project/openapi.json
```

To install a binary, run `go build -o devpilot-openapi .` from `tools/openapi-inspect/`. On Windows, use `devpilot-openapi.exe`.

If given a directory, the tool searches up to four directory levels for `openapi*.json` and `swagger*.json`, skipping vendor/build/cache/hidden directories. You can also pass an explicit JSON file path. The output identifies HTTP methods, paths and `operationId` values. Findings are based on verifiable source evidence: invalid JSON, unsupported version, duplicate operation IDs, missing local `$ref` pointers and malformed path items. External references are **reported but not dereferenced**.

`--json` produces structured output. By default warnings are non-fatal; `--strict` fails on warnings for CI use. Malformed/unsupported specifications return a failure exit status. The module does not require a local Docker engine, running services, an API key or an AI model.

## Threat model and limitations

- Read-only: does not execute project scripts, shell commands, plugins, downloads or HTTP requests.
- Does not follow symlinked files or directories.
- Rejects spec files larger than 5 MiB and bounds directory/file traversal and JSON node inspection.
- Does not interpret or validate the full OpenAPI schema, resolve remote/file references, or promise a service exists or works.
- The displayed endpoints describe **documented** routes, not observed network traffic.
- JSON only for this initial slice; YAML support should use a well-maintained parser after explicit dependency review.

## Test

```sh
cd tools/openapi-inspect
go test ./...
go vet ./...
```

Future integration should expose this inspector via the DevPilot CLI or local UI without weakening the read-only default.
