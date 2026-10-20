# Contributing to DevPilot

Before starting, check existing issues and open pull requests. Prefer small independent tasks with a verifiable developer benefit.

Develop on feature branches; never push directly to `main`, rewrite other agents' branches, or merge without authorization.

For changes to parsers or diagnostics, include tests covering valid files, malformed content, symlinks and size limits. Preserve the default read-only behavior of `devpilot doctor`.

Local checks:

```sh
go test ./...
go vet ./...
go build ./cmd/devpilot
```

Each PR should explain the user problem, evidence, testing performed, and security considerations. Read [SECURITY.md](SECURITY.md) for security disclosures.
