# DevPilot CLI implementations

DevPilot currently contains **two independently maintained CLIs**. Until they are consolidated, use the explicit invocation that matches your intended tool.

| CLI | Language | Launch | Features |
| --- | --- | --- | --- |
| Main CLI | Python 3.10+ | `python -m pip install . && devpilot --help` | Repository analysis, environment doctor, Git and Docker information, TCP checks, opt-in tests |
| Native CLI | Go 1.23+ | `go run ./cmd/devpilot --help` | Read-only doctor, recursive project/CI inventory, read-only Docker diagnostics, opt-in tests |

## Examples

**Python CLI** (installed command):

```sh
devpilot analyze --path .
devpilot doctor --path . --json
devpilot docker
devpilot test --path .      # discover without running
devpilot test --path . --yes # execute only in a trusted project
```

**Go CLI** (explicit invocation avoids command-name collisions):

```sh
go run ./cmd/devpilot analyze --json .
go run ./cmd/devpilot doctor --json .
go run ./cmd/devpilot docker --json
go run ./cmd/devpilot docker --json ps
go run ./cmd/devpilot test --trust . # only in a trusted project
```

For Bundler projects with an RSpec marker (`.rspec` or `spec/spec_helper.rb`), the Python CLI discovers `bundle exec rspec` with `devpilot test --ecosystem ruby`. Discovery is read-only; execution still requires `--yes`.

The two CLIs do **not** share flag syntax: the Python CLI uses `--path` and requires `--yes` to execute tests; the Go CLI takes a positional path and requires `--trust`. Do not copy commands between them.

Go doctor never runs repository scripts. Its .NET test discovery selects an unambiguous project or solution; running any discovered test requires `--trust`. Python analysis skips symlinked and generated directories; read its documentation before evaluating untrusted repositories.

## Maintainer notes

- Python CI: `.github/workflows/ci.yml`; Go CI: `.github/workflows/go-ci.yml`.
- Preserve test coverage for both entry points until one intentionally supersedes the other.
- Do not remove or silently redirect commands during consolidation. First document the compatibility plan, migrate capabilities, add regression tests, and update installation instructions.
- See `docs/go-analyze.md`, `docs/docker.md`, and `SECURITY.md` for details.
