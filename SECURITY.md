# Security policy

DevPilot analyzes **untrusted repository content**. The default `doctor` command reads metadata and may invoke read-only Git commands; it does not run installers, build scripts or application code. `--run-tests` requires `--trust-workspace` and runs code from the repository with the current user's permissions. **This is not sandboxing.** Never enable test execution on untrusted repositories or as a privileged user.

The tool does not upload files or store credentials. Manifest and environment template processing has size limits; environment template values do not appear in reports. Test output is truncated and redacted on a best-effort basis but can still disclose project secrets: review it before sharing.

To report a vulnerability, use GitHub's private vulnerability reporting feature if enabled or contact the maintainer privately rather than posting exploit details publicly. Include the version, impact, minimal reproduction and mitigation guidance.
