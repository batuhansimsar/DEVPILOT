# Security Policy

DevPilot works with untrusted developer projects and potentially sensitive local files.

## Reporting vulnerabilities

Do not disclose exploitable vulnerabilities publicly. Use GitHub private vulnerability reporting if enabled, or contact the maintainer privately using a contact method published on their GitHub profile. Never include secrets or confidential project data in a public report.

## Supported versions

This is a pre-release bootstrap. No long-term support branches are promised.

## Precautions

- `devpilot doctor` reads bounded local metadata and may invoke `git status`. It does not install packages, run project scripts or access the network.
- `devpilot test --trust` executes project-owned code as the current user. Only run this after reviewing and trusting the repository.
- No AI API key, network account or administrator access is needed for `doctor`.
- Environment values are not printed, but diagnostic key names should still be reviewed before sharing.

See [architecture](docs/ARCHITECTURE.md) for trust boundaries.
