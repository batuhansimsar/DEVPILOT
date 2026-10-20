# Offline GitHub Actions pinning audit

Run `devpilot ci-audit .` or `devpilot ci-audit --json .` to inspect literal third-party `uses:` references in `.github/workflows/*.yml` and `.yaml`.

The report identifies actions referenced by a mutable version tag or branch rather than an immutable 40-character Git commit SHA. It includes the workflow path, line number, literal reference and a suggested remedy. A warning means **mutable**, not malicious. Local `./` actions and `docker://` references are excluded from this GitHub Action-specific check.

This is a narrow syntax-based check, **not a YAML parser or a full security scanner**. It does not resolve expressions, nested reusable workflows, repository permissions, or the security properties of pinned code. Review full workflows manually or use specialized security tooling for broader assurance.

Safety: no commands, workflows or network requests run; only regular files are read, symlinks are skipped, each file is capped at 1 MiB, and the scan is limited to 100 directory entries. JSON output never includes file contents or secrets. Exit code 0 means no findings, 1 means mutable references or a partial scan, and 2 means invalid input.
