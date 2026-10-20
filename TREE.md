# Read-only project tree

This independently testable slice adds `devpilot-tree`, a single-binary repository structure viewer. Once the core CLI bootstrap PR is merged, the same `internal/projecttree` package can be wired into the main `devpilot tree` command without duplication.

```sh
go run ./cmd/devpilot-tree --depth 3 --limit 500 /path/to/project
go run ./cmd/devpilot-tree --json /path/to/project
```

The command never executes project scripts, reads file content, follows symlinked directories, or contacts the network. It hides dotfiles unless `--hidden` is set and skips scanning common dependency/build directories. It limits recursion to depth 20 and at most 10,000 entries; defaults are depth 2 and 500 entries. Path **names** may still contain confidential information, so use discretion sharing JSON output.

Run `go test ./...` and `go vet ./...` for verification.
