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
from threading import TIMEOUT_MAX, Thread
from typing import BinaryIO

MAX_OUTPUT_BYTES = 20_000
_READ_BYTES = 8192


def _capture_tail(stream: BinaryIO, tail: bytearray, totals: list[int], read_failed: list[bool]) -> None:
    """Always drain a pipe; retain only its last MAX_OUTPUT_BYTES bytes."""
    try:
        while chunk := os.read(stream.fileno(), _READ_BYTES):
            totals[0] += len(chunk)
            tail.extend(chunk)
            if len(tail) > MAX_OUTPUT_BYTES:
                del tail[:-MAX_OUTPUT_BYTES]
    except (OSError, ValueError):
        # A failed reader must not look like a complete, empty stream.
        read_failed[0] = True
    finally:
        # Close in the reader thread to avoid blocking on a read lock
        # held by a pipe with an inherited writer. A failed close must not
        # silently look like successfully captured output.
        try:
            stream.close()
        except (OSError, ValueError):
            read_failed[0] = True


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
    # Reject an empty executable, invalid types, and embedded NULs before Popen.
    # Empty *positional arguments* are legal and must be forwarded unchanged.
    if (not isinstance(argv, list) or not argv or not isinstance(argv[0], str)
            or not argv[0] or any(not isinstance(arg, str) or '\x00' in arg
                                    for arg in argv)):
        return {**result, 'error': 'argv must contain a nonempty executable and string arguments without NUL bytes'}
    # Validate before Popen: subprocess.wait() can raise for NaN or invalid
    # timeouts after the child has started, leaving it running unsupervised.
    try:
        valid_timeout = (
            not isinstance(timeout, bool)
            and isinstance(timeout, (int, float))
            and math.isfinite(timeout)
            and 0 < timeout <= TIMEOUT_MAX
        )
    except (OverflowError, TypeError, ValueError):
        valid_timeout = False
    if not valid_timeout:
        return {**result, 'error': 'timeout must be a positive finite number of seconds within the platform limit'}
    try:
        process = subprocess.Popen(
            argv, cwd=root, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False,
            start_new_session=(os.name == 'posix'),
        )
    except OSError as exc:
        return {**result, 'error': _safe_spawn_error(exc)}
    except (TypeError, ValueError):
        # Popen may reject an invalid cwd (including embedded NULs) with
        # these exceptions. Keep private paths out of diagnostic errors.
        return {**result, 'error': 'Cannot start command: invalid working directory or process arguments'}

    stdout_tail = bytearray()
    stderr_tail = bytearray()
    stdout_total = [0]
    stderr_total = [0]
    stdout_read_failed = [False]
    stderr_read_failed = [False]
    assert process.stdout is not None and process.stderr is not None
    threads = [
        Thread(target=_capture_tail, args=(process.stdout, stdout_tail, stdout_total, stdout_read_failed), daemon=True),
        Thread(target=_capture_tail, args=(process.stderr, stderr_tail, stderr_total, stderr_read_failed), daemon=True),
    ]
    for thread in threads:
        thread.start()
    try:
        result['exit_code'] = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        # If signaling a POSIX process group is denied, still try to kill the
        # direct child. Never wait indefinitely when termination has failed.
        termination_failed = False
        try:
            if os.name == 'posix':
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass  # Process group has already exited.
                except OSError:
                    process.kill()
            else:
                process.kill()
        except ProcessLookupError:
            pass
        except OSError:
            termination_failed = True
        if not termination_failed:
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                termination_failed = True
        result['error'] = f'Timed out after {timeout}s'
        if termination_failed:
            result['error'] += '; unable to confirm process termination'
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
    result['stdout_truncated'] = stdout_total[0] > MAX_OUTPUT_BYTES or stdout_trimmed or incomplete_streams[0] or stdout_read_failed[0]
    result['stderr_truncated'] = stderr_total[0] > MAX_OUTPUT_BYTES or stderr_trimmed or incomplete_streams[1] or stderr_read_failed[0]
    if stdout_read_failed[0] or stderr_read_failed[0]:
        # Exit code zero alone is not proof that diagnostics were captured.
        # Never include the underlying OSError, which could contain a path.
        result.setdefault('error', 'Cannot capture command output')
    elif any(incomplete_streams):
        # Descendants may keep inherited pipe handles open after the direct
        # child succeeds. Report incomplete capture as an error rather than
        # incorrectly presenting a successful, fully observed test run.
        result.setdefault('error', 'Cannot capture complete command output')
    return result
