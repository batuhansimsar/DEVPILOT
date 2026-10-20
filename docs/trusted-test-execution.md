# Trusted test execution

DevPilot's `doctor` command never runs project code. The separate `test --trust` flow allows intentional execution of repository-defined test commands after the user reviews the workspace.

To reduce accidental credential exposure, the trusted test process now receives an environment with entries omitted when their names include `TOKEN`, `SECRET`, `PASSWORD`, `PASSWD`, `PRIVATE_KEY`, `API_KEY`, `CREDENTIAL`, or `AUTHORIZATION` (case-insensitive). General variables such as `PATH` and `HOME` are retained so toolchains can start.

`exec.CommandContext` terminates the direct process on timeout. A finite `WaitDelay` also prevents indefinite waiting for inherited output pipes when descendants remain alive. This is **not** process-tree termination; descendants can survive a timeout, and the runner is **not sandboxed**.

Untrusted test scripts can still read files in the current user's account and use the network. Sensitive data may reside in variables with other names, in local files, or in agent credentials. Use only with repos you trust. For stronger isolation, execute DevPilot inside a restricted container or dedicated low-privilege account.
