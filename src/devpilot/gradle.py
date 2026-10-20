"""Cross-platform Gradle test command discovery without running project code."""

from __future__ import annotations

import os
from pathlib import Path


def gradle_test_command(root: Path, names: set[str], platform: str) -> tuple[list[str], str]:
    """Prefer a usable local wrapper; never suggest a missing or linked script.

    ``names`` should contain only regular, non-symlinked root files. The
    additional checks here keep this helper safe when used independently.
    """
    if platform == 'nt':
        wrapper = root / 'gradlew.bat'
        if 'gradlew.bat' in names and wrapper.is_file() and not wrapper.is_symlink():
            return [r'.\gradlew.bat', 'test'], 'Gradle Windows wrapper'
    else:
        wrapper = root / 'gradlew'
        if ('gradlew' in names and wrapper.is_file() and not wrapper.is_symlink()
                and os.access(wrapper, os.X_OK)):
            return ['./gradlew', 'test'], 'executable Gradle wrapper'
    return ['gradle', 'test'], 'Gradle project (no usable wrapper)'
