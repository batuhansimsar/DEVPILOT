"""Recognize the Ruby Bundler configuration file that can hold registry tokens.

Callers normalize case, path separators, and editor backup suffixes first.
A generic ``config`` filename is not sensitive outside a ``.bundle`` directory.
"""

from __future__ import annotations


def is_bundler_credential_location(parts: tuple[str, ...]) -> bool:
    """Match the conventional Bundler config path without opening its contents."""
    return len(parts) >= 2 and parts[-2:] == ('.bundle', 'config')
