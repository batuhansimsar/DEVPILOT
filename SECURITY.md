# Security policy

Please report suspected security vulnerabilities privately to the repository maintainers using GitHub's private vulnerability reporting when enabled. If unavailable, contact maintainers without publishing exploit details in a public issue.

DevPilot scans potentially malicious repositories. Passive diagnostics must never execute project code, source `.env` secrets, follow symlinks outside the workspace, or invoke package managers. Test execution requires `--trust` and is **not** a sandbox. Current timeouts terminate the direct process only; child processes may outlive it. Avoid test execution in repositories you do not trust, or use an isolated low-privilege container with no mounted credentials.
