"""Recognize conventional cloud CLI token stores by filename only.

Callers normalize case and path separators before invoking this predicate.
Only specific credential-bearing locations are matched: generic application
config.toml/config.yaml files should not trigger security audit findings.
"""

from __future__ import annotations


_CREDENTIAL_PATH_SUFFIXES = (
    # doctl may persist API tokens in these OS-specific configuration paths.
    ('doctl', 'config.yaml'),
    ('doctl', 'config', 'config.yaml'),
    # Stripe CLI login persists restricted API keys in its XDG configuration.
    ('.config', 'stripe', 'config.toml'),
    # Vercel CLI stores its auth token in this dedicated data directory.
    ('com.vercel.cli', 'auth.json'),
    # Netlify CLI writes an access token to OS-specific global config files.
    ('.config', 'netlify', 'config.json'),
    ('library', 'preferences', 'netlify', 'config.json'),
    ('appdata', 'roaming', 'netlify', 'config', 'config.json'),
)


def is_cloud_cli_credential_location(parts: tuple[str, ...]) -> bool:
    """Identify well-known cloud CLI authentication files."""
    return any(
        len(parts) >= len(suffix) and parts[-len(suffix):] == suffix
        for suffix in _CREDENTIAL_PATH_SUFFIXES
    )
