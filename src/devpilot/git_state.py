"""Interpret Git's stable, read-only porcelain status output."""

from __future__ import annotations


# Git porcelain v1 uses a two-character XY status followed by a space and
# a path. Untracked entries use ??; ignored entries (!!) are not changes.
_STATUS_CODES = frozenset(' MADRCUT')


def _is_porcelain_change(line: str) -> bool:
    """Require an actual changed-file record, not an ignored or torn line."""
    if len(line) < 4 or line[2] != ' ' or not line[3:].strip():
        return False
    code = line[:2]
    return code == '??' or (
        code != '  ' and code[0] in _STATUS_CODES and code[1] in _STATUS_CODES
    )


def _is_complete_ignored_record(line: str) -> bool:
    """An ignored path may be present without making the worktree dirty."""
    return line.startswith('!! ') and bool(line[3:].strip()) and line.endswith('\n')


def is_git_dirty(stdout: str, exit_code: int | None) -> bool | None:
    """Return True for changes, False for clean, None for incomplete output.

    The caller must invoke 'git status --porcelain=v1 --branch'. A complete
    clean result has a valid newline-terminated branch header and, optionally,
    complete ignored-file records (when Git was called with --ignored).
    Unknown or torn output is never proof of a clean tree. Real changes can
    still be identified from a tail missing its branch header.
    """
    if type(exit_code) is not int or exit_code != 0 or not isinstance(stdout, str) or not stdout.strip():
        return None

    # Only `--porcelain=v1 -z` can produce NUL record delimiters. The caller
    # uses line-delimited porcelain v1, which cannot contain a raw NUL.
    # Reject mismatched or corrupted output rather than treating a forged
    # branch header as proof that the worktree is clean.
    if '\x00' in stdout:
        return None

    # Porcelain v1 separates records with LF only. str.splitlines() also treats
    # U+0085, U+2028 and U+2029 inside filenames/branch names as boundaries,
    # allowing an ignored path to masquerade as a changed-file record.
    records = stdout.split('\n')
    lines = [record + '\n' for record in records[:-1]]
    if records[-1]:
        lines.append(records[-1])

    # CRLF is harmless; an embedded CR is not a Git record delimiter and must
    # not let a malformed branch line be accepted as a clean status.
    if any('\r' in (line[:-2] if line.endswith('\r\n') else line) for line in lines):
        return None
    # A torn branch marker is not a porcelain file-status record.
    if any(line.startswith('##') and not line.startswith('## ') for line in lines):
        return None
    if any(_is_porcelain_change(line) for line in lines):
        return True

    if (lines[0].startswith('## ') and lines[0].endswith('\n')
            and lines[0][3:].strip()
            and all(_is_complete_ignored_record(line) for line in lines[1:])):
        return False
    return None
