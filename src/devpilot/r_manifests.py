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
    return bool(stem and not stem.startswith('.') and not any(
        char in '/\\' or ord(char) < 32 or ord(char) == 127
        for char in filename
    ))
