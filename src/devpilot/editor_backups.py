"""Normalize known editor backup wrappers in tracked filenames."""

from __future__ import annotations

import re

_EMACS_NUMBERED_BACKUP = re.compile(r'\.~[0-9]+~\Z')
# Vim starts at .swp and walks backward through .swo, .swn, ..., .swa
# when earlier swap names already exist.
_VIM_SWAP_SUFFIX = re.compile(r'\.sw[a-p]\Z')


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
        if suffix is None and len(name) > 4 and _VIM_SWAP_SUFFIX.search(name):
            suffix = name[-4:]
        if suffix is not None:
            if _VIM_SWAP_SUFFIX.fullmatch(suffix):
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
