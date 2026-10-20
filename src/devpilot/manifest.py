"""Bounded, read-only inspection of untrusted project manifests."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

MAX_MANIFEST_BYTES = 256 * 1024


def _identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    """Identify file replacement and concurrent mutation without reading secrets."""
    return (metadata.st_dev, metadata.st_ino, metadata.st_size,
            metadata.st_mtime_ns, metadata.st_ctime_ns)


def read_package_json(root: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Read at most 256 KiB from a regular package.json without following links.

    lstat avoids opening known symlinks or special files. O_NOFOLLOW, where
    available, also prevents a symlink swap between lstat and open; O_NONBLOCK
    prevents a swapped-in FIFO from hanging the inspector. The second size
    check is required because files can grow after the initial stat.
    """
    manifest = root / 'package.json'
    try:
        metadata = manifest.lstat()
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        return None, f'Cannot inspect package.json: {exc}'
    if not stat.S_ISREG(metadata.st_mode):
        return None, None
    if metadata.st_size > MAX_MANIFEST_BYTES:
        return None, 'package.json exceeds the 256 KiB inspection limit'

    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    try:
        with os.fdopen(os.open(manifest, flags), 'rb') as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode):
                return None, 'package.json is not a regular file'
            if opened.st_size > MAX_MANIFEST_BYTES:
                return None, 'package.json exceeds the 256 KiB inspection limit'
            if _identity(opened) != _identity(metadata):
                return None, 'package.json changed during inspection'
            content = stream.read(MAX_MANIFEST_BYTES + 1)
            if len(content) > MAX_MANIFEST_BYTES:
                return None, 'package.json exceeds the 256 KiB inspection limit'
            if _identity(os.fstat(stream.fileno())) != _identity(opened):
                return None, 'package.json changed during inspection'
        data = json.loads(content.decode('utf-8'))
        if not isinstance(data, dict):
            return None, 'package.json must contain a JSON object'
        return data, None
    except UnicodeDecodeError:
        # The exception string can echo bytes from a manifest containing secrets.
        return None, 'Invalid package.json: must be UTF-8'
    except (OSError, json.JSONDecodeError) as exc:
        return None, f'Invalid package.json: {exc}'
