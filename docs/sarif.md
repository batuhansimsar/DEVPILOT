# Portable SARIF diagnostic export

Run:

    go build -o devpilot ./cmd/devpilot
    ./devpilot doctor --sarif /path/to/project > devpilot.sarif

This option emits SARIF version 2.1.0 without paid AI, network calls, or any new dependency. It preserves the same scan and exit code behavior as ordinary doctor output. The --json and --sarif flags are mutually exclusive.

DevPilot findings are converted into deterministic rule IDs from the existing diagnostic codes, with warning -> warning and info -> note. Passing checks are omitted. Remedies are kept as custom SARIF result properties. No guessed file names, line numbers, or severity upgrades are introduced.

LIMITATION: current doctor findings generally lack verified source-file locations. SARIF permits locationless results, but GitHub code scanning requires a real location to display an alert. Therefore this output is intended for general SARIF inspection/archival, not a promise of GitHub code scanning annotations. A future task can add grounded artifact locations to doctor findings and then populate SARIF locations safely.

Do not upload reports containing sensitive project metadata to public services without reviewing them.
