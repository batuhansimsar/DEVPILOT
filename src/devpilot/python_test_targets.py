"""Limit root-level pytest discovery to explicitly validated test files."""

from __future__ import annotations

from pathlib import Path


def root_pytest_targets(root: Path, max_entries: int) -> list[str] | None:
    """Return explicit root pytest paths, or None for an unsafe/incomplete scan.

    An unqualified pytest invocation also recurses into unrelated directories,
    possibly following nested links to files outside the chosen project root.
    Each target is prefixed with './' to prevent filenames beginning with '-'
    from being treated as command-line options by pytest.
    """
    targets: list[str] = []
    try:
        for count, entry in enumerate(root.iterdir(), 1):
            if count > max_entries or entry.is_symlink():
                return None
            name = entry.name
            if (entry.is_file() and name.endswith('.py')
                    and (name.startswith('test_') or name.endswith('_test.py'))):
                targets.append('./' + name)
    except OSError:
        return None
    return sorted(targets)
