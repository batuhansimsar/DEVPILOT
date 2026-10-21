"""Recognize Cargo registry token files by their conventional path."""

from __future__ import annotations

_CREDENTIAL_FILES = frozenset({'credentials', 'credentials.toml'})


def is_cargo_credential_location(parts: tuple[str, ...]) -> bool:
    """Match Cargo's current and legacy token stores, not generic config files.

    Callers normalize case, separators, and editor backup suffixes first.
    Cargo stores registry authentication in $CARGO_HOME/credentials.toml (or
    the legacy credentials file), normally under a .cargo directory.
    """
    return (len(parts) >= 2 and parts[-2] == '.cargo'
            and parts[-1] in _CREDENTIAL_FILES)
