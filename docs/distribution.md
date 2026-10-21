# Building native CLI snapshots

This is a **build/verification** workflow, not public release automation. It builds a DevPilot CLI for Linux, macOS and Windows on AMD64 and ARM64, bundles README and LICENSE, and writes SHA-256 checksums. Nothing is published, deployed, or merged automatically.

Requires Go, Bash, tar, zip, and sha256sum (or shasum):

```bash
bash scripts/package.sh snapshot dist
(cd dist && sha256sum -c SHA256SUMS) # On macOS, use shasum -a 256 -c SHA256SUMS
```

For a quick local build: `TARGETS='linux/amd64' bash scripts/package.sh snapshot dist` (choose an appropriate target). The `Native CLI snapshots` GitHub Actions workflow runs tests, cross-compiles all six targets, validates their checksums, smoke-tests the Linux AMD64 executable, and retains archives as workflow artifacts for seven days.

Cross-compilation alone does **not** demonstrate runtime compatibility on all target OS/architectures. Those platform checks must be added before claiming official support. The workflow must not be mistaken for a public release pipeline.
