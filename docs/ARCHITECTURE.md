# ADR-0001: Zero-dependency Go diagnostics CLI

**Status:** Initial vertical slice, October 21, 2026.

## Problem

A developer opening an unfamiliar repository needs useful project diagnostics without installing its dependencies, executing its scripts, registering for a hosted service, or buying AI tokens.

## Decision

Use Go standard-library-only packages for the first release:

- `cmd/devpilot`: command-line UX, JSON output, explicit trust gate and test execution.
- `internal/doctor`: bounded read-only manifest, toolchain, Git and environment inspection.
- Structured findings contain severity, codes, concrete evidence and potential remedies.

Choose Go for portable single-binary distribution, straightforward process management and built-in testing. Its costs are that UI capabilities and deeper ecosystem-specific parsing may later justify TypeScript or other adapters. No new runtime is necessary for the current CLI. A React UI will follow only after the diagnostics API and fixtures stabilize.

## Security boundaries

1. The workspace is assumed untrusted and its root is canonicalized.
2. Manifest reads are root-relative, bounded at 1 MiB per file and refuse symlinks and non-regular files.
3. No repository-supplied code runs during `doctor`.
4. Git inspection is read-only and time-limited, disables `core.fsmonitor`, and omits untracked file names.
5. Only environment *key names*, not values, appear in reports; key presence is not credential validity.
6. `devpilot test` runs recognized project-owned commands only after explicit `--trust`, and with a timeout. Tests may execute arbitrary project code with the user's permissions.
7. Tool availability and manifest presence are observations, not guarantees the project builds successfully.

## Current limits

- Root-level only; no monorepo traversal.
- No Docker, service health, architecture graphs, AI agents, or desktop UI yet.
- Cross-compilation is possible but runtime support must be verified by CI before promising any platform.
- No benchmark claims or collected telemetry.

Add integration adapters incrementally, keep expensive or privileged operations opt-in, and test against real sample projects.
