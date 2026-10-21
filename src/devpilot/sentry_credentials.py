"""Recognize Sentry CLI authentication configuration filenames.

These conventional config files can contain auth tokens. Callers must only
inspect filenames, never open or echo their contents.
"""

from __future__ import annotations

_SENTRY_AUTH_FILES = frozenset({'.sentryclirc', 'sentry.properties'})


def is_sentry_auth_config(parts: tuple[str, ...]) -> bool:
    """Identify conventional Sentry authentication stores at any depth.

    Callers normalize path separators, case, and editor backups first.
    """
    return bool(parts) and parts[-1] in _SENTRY_AUTH_FILES
