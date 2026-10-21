"""Stable, JSON-safe metadata boundary for executed test commands."""

from __future__ import annotations

from typing import Any

# Command arguments live in the discovered test plan. Do not copy arbitrary
# runner metadata into command results: it may contain unserializable objects,
# private process state, or a stale copy of the arguments.
_RESULT_FIELDS = ('exit_code', 'stdout', 'stderr', 'error',
                  'stdout_truncated', 'stderr_truncated')


def snapshot_runner_result(result: dict[str, Any]) -> dict[str, Any]:
    """Retain the documented result fields without copying arbitrary objects.

    The caller validates exit codes and text diagnostics after this snapshot.
    All retained fields become immutable JSON scalars at that boundary.
    """
    snapshot = {key: result[key] for key in _RESULT_FIELDS if key in result}
    for flag in ('stdout_truncated', 'stderr_truncated'):
        if flag in snapshot and type(snapshot[flag]) is not bool:
            del snapshot[flag]
            snapshot['error'] = 'Test runner returned invalid capture metadata'
    return snapshot
