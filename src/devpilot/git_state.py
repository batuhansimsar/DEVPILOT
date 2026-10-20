"""Interpret Git's stable, read-only porcelain status output."""

from __future__ import annotations


def is_git_dirty(stdout: str, exit_code: int | None) -> bool | None:
    """Return True for changes, False for clean, and None when Git failed.

    The caller must invoke ``git status --porcelain=v1 --branch``. The first
    line starts with ``## `` and describes the branch, not a file change.
    All subsequent nonempty lines represent staged, unstaged, untracked, or
    unmerged entries. The answer remains conservative if a long status has
    been truncated from the beginning by the command runner.
    """
    if exit_code != 0:
        return None
    return any(line and not line.startswith('## ') for line in stdout.splitlines())
