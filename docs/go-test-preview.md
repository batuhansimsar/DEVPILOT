# Go CLI: preview tests safely

The Go CLI is built with Go 1.23+:

```sh
go build -o devpilot ./cmd/devpilot
./devpilot test --dry-run /path/to/project
```

The `--dry-run` flag discovers the test command, working directory, and
argument boundaries **without running any project executable**, even if
`--trust` is also supplied or the executable is not on `PATH`. Printed
strings are quoted so filenames containing spaces and control characters
are unambiguous. The preview is **not** a shell command to copy and paste.

To execute the discovered tests intentionally, only for a trusted project:

```sh
./devpilot test --trust --timeout=2m /path/to/trusted-project
```

Without `--trust` or `--dry-run`, the Go CLI refuses to run tests.
The `doctor` command remains read-only and never runs test scripts.
