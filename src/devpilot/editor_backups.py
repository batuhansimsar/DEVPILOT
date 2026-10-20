"""Normalize known editor backup wrappers in tracked filenames."""

from __future__ import annotations

import re

_EMACS_NUMBERED_BACKUP = re.compile(r'\\.~[0-9]+~\\Z')


def strip_editor_backups(name: str, suffixes: tuple[str, ...]) -> tuple[str, bool]:
    """Remove nested backup suffixes and Emacs autosave/lock wrappers.

    The filename strictly shrinks on every pass. The returned flag preserves
    Vim's special leading-dot swap-file convention for callers.
    """
    saw_vim_swap = False
    while True:
        numbered = _EMACS_NUMBERED_BACKUP.search(name)
        if numbered is not None:
            if numbered.start() == 0:
                break
            name = name[:numbered.start()]
            continue
        suffix = next((suffix for suffix in suffixes
                       if name.endswith(suffix) and len(name) > len(suffix)), None)
        if suffix is not None:
            if suffix in ('.swp', '.swo', '.swn'):
                saw_vim_swap = True
            name = name[:-len(suffix)]
            continue
        if name.startswith('.#') and len(name) > 2:
            name = name[2:]
            continue
        if name.startswith('#') and name.endswith('#') and len(name) > 2:
            name = name[1:-1]
            continue
        break
    return name, saw_vim_swap
