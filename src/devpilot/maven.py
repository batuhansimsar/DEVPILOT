"""Safe, cross-platform Maven test command discovery without executing files."""

from __future__ import annotations

import os
from pathlib import Path


def maven_test_command(root: Path, names: set[str], platform: str) -> tuple[list[str], str]:
    """Prefer a usable local Maven wrapper, never a missing or linked script.

    Only discovery happens here: running Maven or wrapper scripts still requires
    the CLI's explicit approval for executing commands in a trusted project.
    """
    if platform == 'nt':
        # Maven normally ships mvnw.cmd, but custom Windows projects may use
        # mvnw.bat. Prefer the standard launcher when both are available.
        # Preserve actual casing on case-sensitive development hosts.
        for suffix in ('.cmd', '.bat'):
            for name in sorted(names):
                if name.casefold() != f'mvnw{suffix}':
                    continue
                wrapper = root / name
                if wrapper.is_file() and not wrapper.is_symlink():
                    return [f'.\\{name}', 'test'], 'Maven Windows wrapper'
    else:
        wrapper = root / 'mvnw'
        if ('mvnw' in names and wrapper.is_file() and not wrapper.is_symlink()
                and os.access(wrapper, os.X_OK)):
            return ['./mvnw', 'test'], 'executable Maven wrapper'
    return ['mvn', 'test'], 'Maven project (no usable wrapper)'
