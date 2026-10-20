# Security

Do not submit credentials or private project data in public issues. Report security concerns privately using the repository's GitHub security advisory reporting if enabled, or contact maintainers privately through a verified channel.

The `doctor` command is designed to be read-only and does not execute project scripts. `test --trust` **does execute repository-controlled code** and must only be used on workspaces you trust. Run it without elevated privileges; isolation/sandboxing is not implemented. DevPilot does not inspect `.env` values or persist secrets. Do not give DevPilot broad GitHub permissions.
