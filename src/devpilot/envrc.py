"""Identify potentially secret-bearing direnv configuration names."""

from __future__ import annotations


_TEMPLATE_SUFFIXES = ('.example', '.sample', '.template', '.dist', '.defaults')


def is_sensitive_direnv_file(name: str) -> bool:
    """Recognize .envrc and environment-specific variants, not templates.

    Callers normalize casing and remove editor-backup wrappers first.
    A template marker only exempts the final suffix: `.envrc.example.local`
    can be an active local override and merits review.
    """
    return (name == '.envrc' or name.startswith('.envrc.')) and not name.endswith(_TEMPLATE_SUFFIXES)
