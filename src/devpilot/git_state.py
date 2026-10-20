"""Interpret Git's stable, read-only porcelain status output."""

from __future__ import annotations


# Git porcelain v1 uses a two-character XY status followed by a space and
# a path. Untracked and ignored entries use their own paired markers.
_STATUS_CODES = frozenset(' MADRCUT')


def _is_porcelain_change(line: str) -> bool:
    """Require an actual file record, not arbitrary output or a torn line."""
    if len(line) < 4 or line[2] != ' ' or not line[3:].strip():
        return False
    code = line[:2]
    return code in ('??', '!!') or (
        code != '  ' and code[0] in _STATUS_CODES and code[1] in _STATUS_CODES
    )


def is_git_dirty(stdout: str, exit_code: int | None) -> bool | None:
    """Return True for changes, False for clean, None for incomplete output.

    The caller must invoke 'git status --porcelain=v1 --branch'. A clean
    result has exactly one complete '## <branch>' header ending in a newline.
    Truncated or malformed branch-only output is not proof of a clean tree.
    Changes can still be identified from a tail missing its branch header,
    provided a complete porcelain file-status record remains.
    """
    if exit_code != 0 or not stdout.strip():
        return None

    lines = stdout.splitlines(keepends=True)
    # A torn branch marker is not a porcelain file-status record.
    if any(line.startswith('##') and not line.startswith('## ') for line in lines):
        return None
    if any(_is_porcelain_change(line) for line in lines):
        return True

    if (len(lines) == 1 and lines[0].startswith('## ')
            and lines[0].endswith('\n') and lines[0][3:].strip()):
        return False
    return None
