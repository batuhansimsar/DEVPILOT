"""Run explicit local commands without unbounded stdout/stderr buffering.

This is resource limiting, not a sandbox: trusted test commands can still
access local files or launch child processes.
"""

from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path
from threading import Thread
from typing import BinaryIO

MAX_OUTPUT_BYTES = 20_000
_READ_BYTES = 8192


def _capture_tail(stream: BinaryIO, tail: bytearray, totals: list[int]) -> None:
    """Always drain a pipe; retain only its last MAX_OUTPUT_BYTES bytes."""
    try:
        while chunk := os.read(stream.fileno(), _READ_BYTES):
            totals[0] += len(chunk)
            tail.extend(chunk)
            if len(tail) > MAX_OUTPUT_BYTES:
                del tail[:-MAX_OUTPUT_BYTES]
    except (OSError, ValueError):
        pass
    finally:
        # Close in the reader thread to avoid blocking on a read lock
        # held by a pipe with an inherited writer.
        stream.close()


def run_bounded(argv: list[str], root: Path, timeout: float = 15) -> dict:
    """Execute argv without a shell and return bounded output from each pipe.

    Timeouts kill the spawned process group on POSIX (the direct child on
    Windows). This is not a sandbox; run only trusted project scripts.
    """
    result = {'argv': argv, 'exit_code': None}
    try:
        process = subprocess.Popen(
            argv, cwd=root, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
            start_new_session=(os.name == 'posix'),
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
        if os.name == 'posix':
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass  # Process group has already exited.
        else:
            process.kill()
        process.wait()
        result['error'] = f'Timed out after {timeout}s'
    finally:
        # A child may leave grandchildren holding the pipe ends; never block
        # indefinitely waiting for EOF from those unrelated descendants.
        for thread in threads:
            thread.join(timeout=0.5)
    # Preserve diagnostic output even when a timeout killed the process.
    # Both streams remain bounded and subject to the same truncation flags.
    result['stdout'] = stdout_tail.decode('utf-8', errors='replace')
    result['stderr'] = stderr_tail.decode('utf-8', errors='replace')
    result['stdout_truncated'] = stdout_total[0] > MAX_OUTPUT_BYTES
    result['stderr_truncated'] = stderr_total[0] > MAX_OUTPUT_BYTES
    return result
