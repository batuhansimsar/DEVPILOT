"""Execution policy for explicitly approved project test commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def execute_test_commands(
    commands: list[dict[str, Any]], root: Path, timeout: int,
    runner: Callable[[list[str], Path, int], dict[str, Any]],
    *, fail_fast: bool = False,
) -> bool:
    """Run selected test commands; optionally stop after the first failure.

    When failing fast, retain all discovered commands for the JSON report and
    annotate those not executed rather than representing them as executed.
    """
    if not commands:
        return False
    # A previously run plan may already contain results or fail-fast annotations.
    # Clear them before every run so skipped commands cannot appear executed.
    for item in commands:
        item.pop('result', None)
        item.pop('skipped_reason', None)
    passed = True
    for index, item in enumerate(commands):
        try:
            result = runner(item['argv'], root, timeout)
        except OSError:
            # OS errors may reveal absolute paths or private test arguments.
            # Keep the failure in the report without echoing exception text.
            result = {'exit_code': None, 'error': 'Test command could not be executed (OS error)'}
        item['result'] = result
        exit_code = result.get('exit_code')
        if type(exit_code) is not int or exit_code != 0:
            passed = False
            if fail_fast:
                for skipped in commands[index + 1:]:
                    skipped['skipped_reason'] = 'previous test command failed (--fail-fast)'
                break
    return passed
