# Bounded and redacted test output

DevPilot's read-only `doctor` command never runs project code. The separate `test --trust` command intentionally runs scripts only after explicit approval.

When a trusted test is executed, the CLI now buffers its stdout and stderr separately. Each stream is capped at **256 KiB** before being printed. Overflow is reported with a truncation message. Output is flushed after execution (not streamed live), and this buffering is per stream.

Before printing, DevPilot applies **best-effort** redaction to:
- Values from environment variables whose names contain `TOKEN`, `SECRET`, `PASSWORD`, `PASSWD`, `PRIVATE_KEY`, `API_KEY`, or `CREDENTIAL`.
- Assignment-shaped log values such as `API_TOKEN=...` and `PASSWORD: ...`.
- Common GitHub token prefixes.

**This is not a secret detector, isolation boundary, or guarantee against data leaks.** Unknown secrets, encoded/modified values, and sensitive text lacking a recognizable pattern can still appear. Buffering also changes the UX: output is shown after the command finishes, not interactively. Do not run untrusted project code merely because log redaction exists.

The package `internal/outputguard` is intentionally isolated so it can be reused by later build and test integrations. Tests cover output truncation, normal output, and representative redaction patterns.
