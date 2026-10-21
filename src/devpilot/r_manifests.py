"""Recognize unambiguous R and RStudio project manifests by filename."""

from __future__ import annotations


def is_r_manifest(filename: str) -> bool:
    """Match renv lockfiles and RStudio projects, not backup/lookalike files.

    A plain DESCRIPTION file is not sufficient evidence of an R package:
    non-R projects may also ship a file with that generic name.
    """
    if not isinstance(filename, str):
        return False
    if filename == 'renv.lock':
        return True
    if not filename.endswith('.Rproj'):
        return False
    stem = filename[:-len('.Rproj')]
    # Unsafe filename characters can alter terminal output (bidi controls,
    # line separators, zero-width format characters) even without a slash.
    return bool(stem and not stem.startswith('.') and all(
        char not in '/\\' and char.isprintable() for char in filename
    ))
