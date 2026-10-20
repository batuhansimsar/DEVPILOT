"""Execution policy for explicitly approved project test commands."""

from __future__ import annotations

import subprocess
from copy import deepcopy
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
    Each result is a snapshot: a runner may reuse or mutate its return value
    while executing subsequent commands, but earlier reports must not change.
    Pass independent argument lists so a custom runner cannot corrupt the
    discovered command plan, including when it raises an exception.
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
            # The runner owns this copy, never the command plan used in reports.
            result = runner(list(item['argv']), root, timeout)
        except subprocess.TimeoutExpired:
            # TimeoutExpired may contain the command, output, or private paths;
            # do not serialize exception contents into the JSON report.
            result = {'exit_code': None, 'error': 'Test command timed out'}
        except OSError:
            # OS errors may reveal absolute paths or private test arguments.
            # Keep the failure in the report without echoing exception text.
            result = {'exit_code': None, 'error': 'Test command could not be executed (OS error)'}
        except Exception:
            # Custom runners may raise unexpectedly. Never leak exception text,
            # which can contain credentials, local paths, or captured output.
            result = {'exit_code': None, 'error': 'Test runner failed unexpectedly'}
        if not isinstance(result, dict):
            # Defensive boundary for custom test runners; never crash when a
            # runner accidentally returns None or a non-mapping value.
            result = {'exit_code': None, 'error': 'Test runner returned an invalid result'}
        # Keep each command's report independent of a custom runner's mutable
        # buffer, including nested metadata such as captured output chunks.
        try:
            item['result'] = deepcopy(result)
        except Exception:
            # A custom runner may return objects whose copy hooks raise.
            # Treat the result as a failed command without exposing private data.
            item['result'] = {'exit_code': None, 'error': 'Test runner returned an uncopyable result'}
        exit_code = item['result'].get('exit_code')
        # A custom runner may omit exit_code or return a bool/string. Normalize
        # it before rendering the report, whose human format requires this key.
        if type(exit_code) is not int:
            item['result']['exit_code'] = None
            if not item['result'].get('error'):
                item['result']['error'] = 'Test runner returned an invalid exit code'
            exit_code = None
        # Runner-reported errors invalidate the run even when a subprocess
        # happens to return zero (e.g. a failed output-capture stage).
        if exit_code != 0 or item['result'].get('error'):
            passed = False
            if fail_fast:
                for skipped in commands[index + 1:]:
                    skipped['skipped_reason'] = 'previous test command failed (--fail-fast)'
                break
    return passed
