# Project tree

The `devpilot tree` command provides a **read-only** directory overview even for unfamiliar repositories. It never reads file contents, follows symlinks, runs scripts, or contacts external services.

```sh
devpilot tree .
devpilot tree --depth 2 /path/to/project
devpilot tree --json --depth 4 /path/to/project
```

By default, depth is four directory components. Use `--depth 0` to show only the root, or at most 12 to explore deeper. The scan stops at 5,000 entries and marks truncated reports. It hides typical generated/dependency folders (`.git`, `node_modules`, `vendor`, `dist`, `build`, `target`, and others) and local `.env` / `.env.*` configuration file names. Paths are sorted for consistent output. JSON output is intended for automation and future UI usage.

This is a structure viewer, not a malware scanner or a guarantee that directories are safe to execute.
