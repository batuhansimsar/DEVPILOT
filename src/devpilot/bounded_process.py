"""Run explicit local commands without unbounded stdout/stderr buffering.

This is resource limiting, not a sandbox: trusted test commands can still
access local files or launch child processes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from threading import Thread
from typing import BinaryIO

MAX_OUTPUT_BYTES = 20_000
_READ_BYTES = 8192


def _capture_tail(stream: BinaryIO, tail: bytearray, totals: list[int]) -> None:
    """Always drain a pipe; retain only its last MAX_OUTPUT_BYTES bytes."""
    try:
        while chunk := stream.read(_READ_BYTES):
            totals[0] += len(chunk)
            tail.extend(chunk)
            if len(tail) > MAX_OUTPUT_BYTES:
                del tail[:-MAX_OUTPUT_BYTES]
    except (OSError, ValueError):
        # The caller may close a pipe after a timeout or when a descendant
        # incorrectly keeps an inherited descriptor open.
        pass


def run_bounded(argv: list[str], root: Path, timeout: float = 15) -> dict:
    """Execute argv without a shell and return bounded output from each pipe.

    Killing a timed-out child does not guarantee termination of processes
    spawned by that child; do not run test scripts from untrusted projects.
    """
    result = {'argv': argv, 'exit_code': None}
    try:
        process = subprocess.Popen(
            argv, cwd=root, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
        )
    except OSError as exc:
        return {**result, 'error': str(exc)}

    stdout_tail = bytearray()
    stderr_tail = bytearray()
    stdout_total = [0]
    stderr_total = [0]
    assert process.stdout is not None and process.stderr is not None
    threads = [
        Thread(target=_capture_tail, args=(process.stdout, stdout_tail, stdout_total), daemon=True),
        Thread(target=_capture_tail, args=(process.stderr, stderr_tail, stderr_total), daemon=True),
    ]
    for thread in threads:
        thread.start()
    try:
        result['exit_code'] = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        result['error'] = f'Timed out after {timeout}s'
    finally:
        # A child may leave grandchildren holding the pipe ends; never block
        # indefinitely waiting for EOF from those unrelated descendants.
        for thread in threads:
            thread.join(timeout=0.5)
        for stream in (process.stdout, process.stderr):
            stream.close()
    if 'error' not in result:
        result['stdout'] = stdout_tail.decode('utf-8', errors='replace')
        result['stderr'] = stderr_tail.decode('utf-8', errors='replace')
        result['stdout_truncated'] = stdout_total[0] > MAX_OUTPUT_BYTES
        result['stderr_truncated'] = stderr_total[0] > MAX_OUTPUT_BYTES
    return result
