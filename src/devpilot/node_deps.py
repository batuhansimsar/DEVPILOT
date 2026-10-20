"""Validate and inventory Node.js dependency names without exposing versions."""

from __future__ import annotations

import re

# npm package IDs are URL-safe names, optionally qualified by a scope. Reject
# arbitrary object keys so untrusted URLs, control characters, and credentials
# cannot be mistaken for packages or appear in dependency reports.
_PACKAGE_NAME = re.compile(
    r"(?:@[A-Za-z0-9][A-Za-z0-9._~-]*/)?[A-Za-z0-9][A-Za-z0-9._~-]*\Z"
)
_GROUPS = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")
_BUNDLED_ALIASES = ("bundleDependencies", "bundledDependencies")


def _valid_package_name(name: object) -> bool:
    return isinstance(name, str) and len(name) <= 214 and bool(_PACKAGE_NAME.fullmatch(name))


def parse_node_dependency_groups(manifest: dict[str, object]) -> dict[str, list[str]]:
    """Return sorted npm package names, rejecting malformed dependency sections.

    Errors intentionally contain only trusted group labels, not package names
    or potentially credential-bearing version strings from the manifest.
    """
    groups: dict[str, list[str]] = {}
    for group in _GROUPS:
        entries = manifest.get(group, {})
        if not isinstance(entries, dict):
            raise ValueError(f"package.json {group} must be an object")
        if any(not _valid_package_name(name) for name in entries):
            raise ValueError(f"package.json {group} contains an invalid package name")
        if any(not isinstance(version, str) for version in entries.values()):
            raise ValueError(f"package.json {group} versions must be strings")
        # npm identifiers are case-insensitive in registry resolution. Distinct
        # JSON keys differing only by case would silently report the same
        # dependency twice (possibly with conflicting version requirements).
        if len({name.casefold() for name in entries}) != len(entries):
            raise ValueError(f"package.json {group} contains duplicate case-insensitive package names")
        if entries:
            groups[group] = sorted(entries)
    # npm accepts both spellings and a boolean to bundle all production dependencies.
    # Keep potentially credential-bearing version and source values private.
    aliases = [alias for alias in _BUNDLED_ALIASES if alias in manifest]
    if len(aliases) > 1:
        raise ValueError("package.json defines both bundled dependency aliases")
    if aliases:
        bundled = manifest[aliases[0]]
        if bundled is True:
            names = groups.get("dependencies", [])
        elif bundled is False:
            names = []
        elif isinstance(bundled, list):
            if any(not _valid_package_name(name) for name in bundled):
                raise ValueError("package.json bundled dependencies contain an invalid package name")
            if len({name.casefold() for name in bundled}) != len(set(bundled)):
                raise ValueError("package.json bundled dependencies contain duplicate case-insensitive package names")
            names = sorted(set(bundled))
        else:
            raise ValueError("package.json bundled dependencies must be a list or boolean")
        if names:
            groups["bundleDependencies"] = list(names)
    return groups
