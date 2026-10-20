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
        if any(not isinstance(name, str) or len(name) > 214
               or not _PACKAGE_NAME.fullmatch(name) for name in entries):
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
    return groups
