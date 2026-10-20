# DevPilot Go Test Report

An **offline**, read-only analyzer for `go test -json` output. It complements the initial `devpilot doctor` pull request without modifying or duplicating its CLI. It is a narrow standalone vertical slice until the main DevPilot command schema is stable.

## Run

Requires Go 1.22+, no external modules or AI subscriptions.

```sh
cd tools/gotestreport
go test ./...
go build -o gotestreport .
# In another Go module/project, capture a test run:
go test -json ./... > tests.ndjson
./gotestreport -input tests.ndjson
./gotestreport -input tests.ndjson -format json
# Or pipe a saved NDJSON stream to stdin:
cat tests.ndjson | ./gotestreport -format json
```

`go test` can exit non-zero; capturing its output in a file is the easiest way to keep the report even when tests fail. The standalone tool **never executes** tests itself.

Exit codes: `0` pass; `1` at least one test/package failed; `2` malformed, missing, truncated, or unsafe-sized input, or invalid arguments. A package failure without a failed test often indicates a build or setup error. For security, raw test output is **not** included in either text or JSON reports: logs may contain API keys, tokens, or personal data. Only test and package identifiers, counts, status, and generic next steps are emitted. Untrusted names are terminal-escaped in text output.

### Scope and limitations

- Accepts Go's NDJSON action events, not JUnit XML or an arbitrary JSON array.
- Counts terminal `pass`, `fail` and `skip` events by test identity, including subtests. Package-only failures are reported separately, so a failing test isn't double counted.
- Missing package terminal events are marked `incomplete`, not silently considered passing.
- A failed test is a real failure; diagnostic details still require rerunning tests with trusted local tools. No guesses are made about the root cause.
- Future task: integrate the report as an optional view in DevPilot's standard test workflow after coordinating the parent CLI result schema.
