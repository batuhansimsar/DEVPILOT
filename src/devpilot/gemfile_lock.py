"""Read-only Ruby Gemfile.lock inventory without revealing remote credentials."""

from __future__ import annotations

import re

# Bundler spec versions begin with digits and contain only version/platform
# characters. Do not treat arbitrary parenthesized metadata as locked gems.
_SPEC = re.compile(
    r'^    ([A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?) '
    r'\([0-9][A-Za-z0-9._+-]*\)$'
)
_SEPARATOR = re.compile(r'[-_.]+')
_MAX_GEM_NAME_LENGTH = 214
MAX_GEMFILE_LOCK_CHARS = 1_000_000


def parse_gemfile_lock(content: str) -> list[str]:
    """Read only top-level gem specs inside GEM, GIT, and PATH sections.

    Four-space indented entries under specs: represent resolved gems;
    six-space entries are their nested dependency constraints, not packages.
    Remote URLs, ref hashes, versions and platforms are never included.
    """
    if not isinstance(content, str) or len(content) > MAX_GEMFILE_LOCK_CHARS:
        raise ValueError('Gemfile.lock input is invalid or exceeds safe size limit')
    names: set[str] = set()
    in_source = False
    in_specs = False
    # A UTF-8 BOM at the start is an encoding signature, not part of GEM.
    # splitlines() treats VT, FF, NEL and Unicode LS/PS as newlines even
    # though Bundler lockfiles use physical CR/LF lines. Those characters
    # must not invent GEM/specs sections inside malformed lockfile metadata.
    physical_lines = content.removeprefix('\ufeff').replace('\r\n', '\n').replace('\r', '\n')
    for line in physical_lines.split('\n'):
        if line and not line[0].isspace():
            in_source = line.strip() in {'GEM', 'GIT', 'PATH'}
            in_specs = False
            continue
        # Bundler's specs marker has exactly two spaces. Indented metadata
        # elsewhere in a source section must not restart a specs block.
        if in_source and line == '  specs:':
            in_specs = True
            continue
        if in_specs:
            # Source metadata (remote, revision, branch, etc.) is indented
            # by two spaces. It terminates the current specs block, so a
            # following four-space line cannot masquerade as a locked gem.
            if line.strip() and not line.startswith('    '):
                in_specs = False
                continue
            match = _SPEC.fullmatch(line)
            if match and len(match.group(1)) <= _MAX_GEM_NAME_LENGTH:
                names.add(_SEPARATOR.sub('-', match.group(1)).lower())
    return sorted(names)
