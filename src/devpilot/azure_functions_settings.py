"""Recognize Azure Functions local settings files without reading secrets.

The callers supply lowercase, separator-normalized path components after
removing editor backup suffixes. Azure Functions' ``local.settings.json`` can
store connection strings and app settings under ``Values``. Flag only that
conventional basename to avoid noisy alerts for generic settings files.
"""

from __future__ import annotations


def is_azure_functions_local_settings(parts: tuple[str, ...]) -> bool:
    """Return whether a normalized path names Azure Functions local settings."""
    return bool(parts) and parts[-1] == 'local.settings.json'
