"""Recognize private registration credentials of self-hosted GitHub Actions runners.

The audit callers normalize Git paths and strip editor backup suffixes first.
Only conventional runner installation directories are matched because the
credential basenames are ambiguous in unrelated projects.
"""

from __future__ import annotations

_RUNNER_DIRECTORIES = frozenset({'actions-runner', '.actions-runner'})
_RUNNER_CREDENTIALS = frozenset({'.credentials', '.credentials_rsaparams'})


def is_actions_runner_credential_location(parts: tuple[str, ...]) -> bool:
    """Match a runner's local auth token or RSA private-key parameters file."""
    return (len(parts) >= 2 and parts[-2] in _RUNNER_DIRECTORIES
            and parts[-1] in _RUNNER_CREDENTIALS)
