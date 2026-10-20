"""Interpret Git's stable, read-only porcelain status output."""

from __future__ import annotations


def is_git_dirty(stdout: str, exit_code: int | None) -> bool | None:
    """Return True for changes, False for clean, None for incomplete output.

    The caller must invoke 'git status --porcelain=v1 --branch'. A clean
    result has exactly one complete '## <branch>' header ending in a newline.
    Truncated or malformed branch-only output is not proof of a clean tree.
    Changes can still be identified from a tail missing its branch header.
    """
    if exit_code != 0 or not stdout.strip():
        return None

    lines = stdout.splitlines(keepends=True)
    # A torn branch marker is not a porcelain file-status record.
    if any(line.startswith('##') and not line.startswith('## ') for line in lines):
        return None
    if any(line.strip() and not line.startswith('## ') for line in lines):
        return True

    if (len(lines) == 1 and lines[0].startswith('## ')
            and lines[0].endswith('\n') and lines[0][3:].strip()):
        return False
    return None
