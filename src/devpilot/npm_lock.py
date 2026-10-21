"""Read-only, privacy-safe package inventory for npm lockfiles.

Support legacy npm v1 dependency trees and modern v2/v3 installed-package
maps without returning versions, integrity hashes, or registry URLs.
"""

from __future__ import annotations

import json

from .json_numbers import parse_finite_json_float
from .node_deps import _valid_package_name

# The dependency scanner limits files to 512 KB, but direct parser callers
# need an independent limit before json.loads allocates memory.
MAX_NPM_LOCK_INPUT_CHARS = 2 * 1024 * 1024


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('npm lockfile contains duplicate JSON keys')
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError('npm lockfile contains a non-finite number')


# This is below CPython's default integer-string limit and is applied also on
# versions where that limit is absent or disabled. Large numeric metadata is
# not meaningful to a package-name inventory, but can consume CPU and memory.
_MAX_JSON_INTEGER_DIGITS = 1024


def _bounded_int(value: str) -> int:
    """Decode JSON integers with a portable size cap and redacted errors."""
    if len(value.lstrip('-')) > _MAX_JSON_INTEGER_DIGITS:
        raise ValueError('npm lockfile contains an oversized integer')
    try:
        return int(value)
    except (ValueError, OverflowError):
        raise ValueError('npm lockfile contains an invalid integer') from None


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
    # Validate each ancestor package in a nested node_modules chain. A
    # malformed ancestor must not be ignored just because the leaf is valid.
    installed = None
    for index, position in enumerate(positions):
        end = positions[index + 1] if index + 1 < len(positions) else len(parts)
        tail = parts[position + 1:end]
        if len(tail) == 1:
            name = tail[0]
        elif len(tail) == 2 and tail[0].startswith('@'):
            name = '/'.join(tail)
        else:
            raise ValueError('npm lockfile contains an invalid installed package path')
        if not _valid_package_name(name):
            raise ValueError('npm lockfile contains an invalid package name')
        installed = name
    return installed

def parse_npm_lock(content: str) -> list[str]:
    """Return unique installed package names from package-lock/shrinkwrap JSON.

    Never read or emit value fields: they can contain authentication tokens,
    private registry URLs, or integrity strings. Reject malformed structures
    without printing any untrusted package names or source text.
    """
    if not isinstance(content, str) or len(content) > MAX_NPM_LOCK_INPUT_CHARS:
        raise ValueError('npm lockfile input exceeds safe size limit or is invalid')
    try:
        document = json.loads(content.removeprefix('\ufeff'),
                              object_pairs_hook=_unique_keys,
                              parse_constant=_reject_constant,
                              parse_float=parse_finite_json_float,
                              parse_int=_bounded_int)
    except (json.JSONDecodeError, RecursionError):
        raise ValueError('invalid npm lockfile JSON') from None
    if not isinstance(document, dict):
        raise ValueError('npm lockfile root must be an object')

    # An explicit npm lockfile version must be an integer supported by this
    # parser. In particular, booleans compare equal to integers in Python,
    # but true/false and null are not valid lockfile versions. Do not infer an
    # inventory from an unsupported future format or a malformed manifest.
    if 'lockfileVersion' in document:
        version = document['lockfileVersion']
        if type(version) is not int or version not in (1, 2, 3):
            raise ValueError('npm lockfile has an unsupported lockfileVersion')

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
