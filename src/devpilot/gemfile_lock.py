"""Read-only Ruby Gemfile.lock inventory without revealing remote credentials."""

from __future__ import annotations

import re

_SPEC = re.compile(r'^    ([A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?) \([^\r\n]*\)$')
_SEPARATOR = re.compile(r'[-_.]+')


def parse_gemfile_lock(content: str) -> list[str]:
    """Read only top-level gem specs inside GEM, GIT, and PATH sections.

    Four-space indented entries under specs: represent resolved gems;
    six-space entries are their nested dependency constraints, not packages.
    Remote URLs, ref hashes, versions and platforms are never included.
    """
    names: set[str] = set()
    in_source = False
    in_specs = False
    for line in content.splitlines():
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
            if match:
                names.add(_SEPARATOR.sub('-', match.group(1)).lower())
    return sorted(names)
