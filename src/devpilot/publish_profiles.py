"""Identify .NET publish profiles that may include deployment credentials.

This predicate examines filenames only; it never opens publish profiles.
Callers normalize case, separators, and editor backup suffixes first.
"""

from __future__ import annotations


def is_publish_profile(parts: tuple[str, ...]) -> bool:
    """Match standard MSBuild PublishProfiles files, not unrelated XML files.

    Both .pubxml and .pubxml.user files can include publish passwords or
    service connection details, so tracked copies warrant manual review.
    """
    return (
        len(parts) >= 3
        and parts[-3:-1] == ('properties', 'publishprofiles')
        and parts[-1].endswith(('.pubxml', '.pubxml.user'))
    )
