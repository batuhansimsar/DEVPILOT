# Security Policy

DevPilot inspects potentially hostile repositories. **Do not run `devpilot test --trust` on untrusted code.** Tests are arbitrary processes and may read credentials, modify files, or spawn child processes even with a timeout.

If you find a security issue, use the repository's private security advisory reporting flow where available, or contact the maintainers privately. Do not publish exploit details until coordinated disclosure is complete. The initial 0.1 milestone is not a hardened sandbox and makes no security guarantees about code explicitly executed with `--trust`.
