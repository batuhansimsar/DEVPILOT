"""Use installed distribution metadata for the CLI version where available."""

from __future__ import annotations

from importlib import metadata

from . import __version__


def cli_version() -> str:
    """Report the installed version; support uninstalled source checkouts.

    Keeping the CLI's version tied to distribution metadata prevents the
    `--version` option from becoming stale after a packaging version bump.
    """
    try:
        release = metadata.version('devpilot-cli')
    except metadata.PackageNotFoundError:
        release = __version__
    return f'devpilot {release}'
