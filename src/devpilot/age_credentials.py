"""Recognize conventional age private identity files by location, not contents."""

from __future__ import annotations

# age identity material is commonly stored here by age and SOPS. keys.txt
# is too generic to classify outside these specific credential directories.
_IDENTITY_SUFFIXES = (
    ('.config', 'sops', 'age', 'keys.txt'),
    ('.config', 'age', 'keys.txt'),
)


def is_age_identity_path(parts: tuple[str, ...]) -> bool:
    """Check normalized, lowercase path segments after backup suffix removal."""
    return any(parts[-len(suffix):] == suffix for suffix in _IDENTITY_SUFFIXES)
