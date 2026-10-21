"""Bound and validate importable package trees for root-level unittest discovery."""

from __future__ import annotations

from pathlib import Path

from .scan_root import ensure_unlinked_scan_path


MAX_UNITTEST_DISCOVERY_ENTRIES = 4096


def root_unittest_imports_are_safe(root: Path) -> bool:
    """Reject linked or unreadable files reachable by root-level unittest discovery.

    Unlike discovery scoped to tests/, a root-level unittest run descends into
    every importable package. Check those packages recursively before offering
    the command, without traversing non-packages or following links. Reject
    linked roots and ancestors too, including when called independently of the
    test command selector.
    """
    try:
        ensure_unlinked_scan_path(root)
    except (ValueError, OSError):
        return False

    pending = [root]
    inspected = 0
    try:
        while pending:
            for entry in pending.pop().iterdir():
                inspected += 1
                if inspected > MAX_UNITTEST_DISCOVERY_ENTRIES or entry.is_symlink():
                    return False
                if entry.is_dir():
                    marker = entry / '__init__.py'
                    if marker.is_symlink():
                        return False
                    if marker.is_file():
                        pending.append(entry)
                elif not entry.is_file():
                    return False
    except OSError:
        return False
    return True
