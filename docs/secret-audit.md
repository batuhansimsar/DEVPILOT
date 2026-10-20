# Tracked credential audit

DevPilot includes a standalone, read-only security check for **tracked filenames** that look like credentials or private keys.

Run from a Git repository:

    python -m devpilot.secret_audit .
    python -m devpilot.secret_audit . --json
    python -m devpilot.secret_audit . --json --redact-paths

It searches Git's tracked index for names such as .env, environment-specific configuration, private key formats (.pem, .p12, .pfx, .key, .kdbx), service-account JSON and known credential config filenames. Example/sample files are excluded where possible.

The command **never reads file contents**, does not access the network, and does not change the repository. It skips untracked files; it is not a full secrets scanner or proof of compromise. All findings are heuristics and need human review.

Exit status: 0 means no suspicious tracked filenames, 1 means potential risks found, 2 means invocation or Git inspection failed. The --redact-paths option excludes filenames from the finding list for safer automation logs.

If a sensitive file was committed, removing it from the current version is not enough: assess exposure, revoke/rotate credentials and, if appropriate, coordinate history cleanup with repository maintainers.
