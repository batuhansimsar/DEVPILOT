# Security Policy

This project is at an early stage and has no stable release or security support window. Please report sensitive vulnerabilities privately using GitHub's private vulnerability reporting feature, if enabled, or contact the repository maintainer without posting exploit details publicly.

`devpilot doctor` is read-only and never starts project code. `devpilot test --trust` explicitly runs detected project test commands; those may run arbitrary code and **are not sandboxed**. Only use this flag on a trusted workspace. Files in a repository, especially manifests and scripts, must be treated as untrusted. Do not publish secrets in issues or test logs.
