"""Normalize known editor backup wrappers in tracked filenames."""

from __future__ import annotations

import re

_EMACS_NUMBERED_BACKUP = re.compile(r'\.~[0-9]+~\Z')
# Vim starts at .swp and rotates down through .swa, then .svz to .sva,
# continuing through .suz ... .saa if every preceding swap name is occupied.
# Restrict the initial .sw group to a-p: .swq and .swz are not Vim swaps.
_VIM_SWAP_SUFFIX = re.compile(r'\.s(?:w[a-p]|[a-v][a-z])\Z')
# JetBrains IDEs create these copies while safely replacing an edited file.
_JETBRAINS_SAFE_WRITE_SUFFIXES = ('.___jb_tmp___', '.___jb_old___')


def strip_editor_backups(name: str, suffixes: tuple[str, ...]) -> tuple[str, bool]:
    """Remove nested editor backup, autosave, and safe-write wrappers.

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
        suffix = next((suffix for suffix in (*suffixes, *_JETBRAINS_SAFE_WRITE_SUFFIXES)
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
