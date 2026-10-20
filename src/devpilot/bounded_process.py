"""Run explicit local commands without unbounded stdout/stderr buffering.

This is resource limiting, not a sandbox: trusted test commands can still
access local files or launch child processes.
"""

from __future__ import annotations

import errno
import math
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


def _decode_bounded(tail: bytearray) -> tuple[str, bool]:
    """Return UTF-8-safe output without expanding beyond the byte budget.

    Replacing malformed input with U+FFFD can triple the encoded size. Trim
    from the left *after* replacement to keep the latest diagnostic output.
    A cut through a UTF-8 sequence is dropped rather than adding new bytes.
    """
    decoded = tail.decode('utf-8', errors='replace')
    encoded = decoded.encode('utf-8')
    if len(encoded) <= MAX_OUTPUT_BYTES:
        return decoded, False
    return encoded[-MAX_OUTPUT_BYTES:].decode('utf-8', errors='ignore'), True

def _safe_spawn_error(error: OSError) -> str:
    """Expose only an errno name, never sensitive filenames or OS messages."""
    code = errno.errorcode.get(error.errno, 'I/O error')
    return f'Cannot start command: {code}'


def run_bounded(argv: list[str], root: Path, timeout: float = 15) -> dict:
    """Execute argv without a shell and return bounded output from each pipe.

    Timeouts kill the spawned process group on POSIX (the direct child on
    Windows). This is not a sandbox; run only trusted project scripts.
    """
    result = {'argv': argv, 'exit_code': None}
    # Never hand an invalid command to Popen: empty sequences, embedded NULs,
    # and non-string arguments can raise uncaught IndexError/ValueError/TypeError.
    if (not isinstance(argv, list) or not argv
            or any(not isinstance(arg, str) or not arg or '\x00' in arg for arg in argv)):
        return {**result, 'error': 'argv must be a nonempty list of nonempty strings without NUL bytes'}
    # Validate before Popen: subprocess.wait() can raise for NaN or invalid
    # timeouts after the child has started, leaving it running unsupervised.
    try:
        valid_timeout = (
            not isinstance(timeout, bool)
            and isinstance(timeout, (int, float))
            and math.isfinite(timeout)
            and timeout > 0
        )
    except (OverflowError, TypeError, ValueError):
        valid_timeout = False
    if not valid_timeout:
        return {**result, 'error': 'timeout must be a positive finite number of seconds'}
    try:
        process = subprocess.Popen(
            argv, cwd=root, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
            start_new_session=(os.name == 'posix'),
        )
    except OSError as exc:
        return {**result, 'error': _safe_spawn_error(exc)}

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
    # A descendant can inherit a pipe and outlive the direct child. In that
    # case the bounded join returns before EOF, so captured output is not
    # complete even if it never reached the byte cap.
    incomplete_streams = [thread.is_alive() for thread in threads]
    # Preserve diagnostic output even when a timeout killed the process.
    # Both streams remain bounded and subject to the same truncation flags.
    result['stdout'], stdout_trimmed = _decode_bounded(stdout_tail)
    result['stderr'], stderr_trimmed = _decode_bounded(stderr_tail)
    result['stdout_truncated'] = stdout_total[0] > MAX_OUTPUT_BYTES or stdout_trimmed or incomplete_streams[0]
    result['stderr_truncated'] = stderr_total[0] > MAX_OUTPUT_BYTES or stderr_trimmed or incomplete_streams[1]
    return result
