# Go CLI JSON Test Plans

Use the Go CLI to discover how a trusted repository would be tested **without executing a test process**:

```bash
go run ./cmd/devpilot test --dry-run --json /path/to/project
```

Example output (paths and commands depend on the project):

```json
{
  "arguments": ["test", "./..."],
  "executable": "go",
  "executed": false,
  "working_directory": "/path/to/project"
}
```

`arguments` is a structured array, not a shell command. Tool installation is not required to preview a plan. Use `--dry-run` without `--json` for a human-readable preview. The `--json` flag applies only to test preview; `--trust` and `--dry-run` cannot be combined. Only `test --trust` executes project code. Do not run it on repositories you do not trust.
