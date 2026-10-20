# Security policy

DevPilot reads untrusted repositories. Static inspection avoids executing workspace commands, but any parser can have defects. `devpilot test --run --trust-workspace` executes project test commands and can run arbitrary code. **The trust flag is not a sandbox.** Never run tests from unknown repositories without proper operating-system isolation.

Never commit tokens or .env files. DevPilot does not need credentials for local analysis. Report vulnerabilities privately through GitHub's private vulnerability reporting if enabled. We cannot yet promise a fixed response SLA.
