"""Read-only, privacy-safe package inventory for npm lockfiles.

Support legacy npm v1 dependency trees and modern v2/v3 installed-package
maps without returning versions, integrity hashes, or registry URLs.
"""

from __future__ import annotations

import json

from .json_numbers import parse_finite_json_float
from .node_deps import _valid_package_name


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('npm lockfile contains duplicate JSON keys')
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError('npm lockfile contains a non-finite number')


def _installed_name(path: str) -> str | None:
    """Extract a package ID, ignoring root/workspace metadata entries."""
    if not path:
        # The root project's metadata is stored under the empty key.
        return None
    parts = path.split('/')
    # npm serializes POSIX-style relative paths.  Without this guard,
    # traversal, absolute, or malformed ancestors can masquerade as valid
    # installed packages because only the final node_modules was inspected.
    if ('\\' in path or any(part in ('', '.', '..') for part in parts)):
        raise ValueError('npm lockfile contains an invalid installed package path')
    positions = [index for index, segment in enumerate(parts) if segment == 'node_modules']
    if not positions:
        return None
    # A lockfile path must be a normalized relative path. Without this check,
    # traversal or empty segments can hide an invalid entry behind a valid
    # final node_modules/package suffix and produce a misleading inventory.
    if any(segment in ('', '.', '..') for segment in parts):
        raise ValueError('npm lockfile contains an invalid installed package path')
    tail = parts[positions[-1] + 1:]
    if len(tail) == 1:
        name = tail[0]
    elif len(tail) == 2 and tail[0].startswith('@'):
        name = '/'.join(tail)
    else:
        raise ValueError('npm lockfile contains an invalid installed package path')
    if not _valid_package_name(name):
        raise ValueError('npm lockfile contains an invalid package name')
    return name


def parse_npm_lock(content: str) -> list[str]:
    """Return unique installed package names from package-lock/shrinkwrap JSON.

    Never read or emit value fields: they can contain authentication tokens,
    private registry URLs, or integrity strings. Reject malformed structures
    without printing any untrusted package names or source text.
    """
    try:
        document = json.loads(content.removeprefix('\ufeff'),
                              object_pairs_hook=_unique_keys,
                              parse_constant=_reject_constant,
                              parse_float=parse_finite_json_float)
    except (json.JSONDecodeError, RecursionError):
        raise ValueError('invalid npm lockfile JSON') from None
    if not isinstance(document, dict):
        raise ValueError('npm lockfile root must be an object')

    names: set[str] = set()
    if 'packages' in document:
        packages = document['packages']
        if not isinstance(packages, dict):
            raise ValueError('npm lockfile packages must be an object')
        for path, details in packages.items():
            if not isinstance(details, dict):
                raise ValueError('npm lockfile package entries must be objects')
            name = _installed_name(path)
            if name is not None:
                names.add(name)
    else:
        # v1 lockfiles nest transitive requirements in each dependency object.
        # Traverse iteratively so a hostile or unusually deep tree cannot
        # overflow the Python stack during inventorying.
        dependencies = document.get('dependencies', {})
        stack = [dependencies]
        while stack:
            entries = stack.pop()
            if not isinstance(entries, dict):
                raise ValueError('npm lockfile dependencies must be objects')
            for name, details in entries.items():
                if not _valid_package_name(name):
                    raise ValueError('npm lockfile contains an invalid package name')
                if not isinstance(details, dict):
                    raise ValueError('npm lockfile dependency entries must be objects')
                names.add(name)
                if 'dependencies' in details:
                    stack.append(details['dependencies'])
    return sorted(names)
