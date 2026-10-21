"""Read-only discovery of RSpec test commands for Bundler projects."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def ruby_test_command(root: Path, names: set[str]) -> dict[str, Any] | None:
    """Select RSpec only when both Bundler and RSpec are explicitly indicated.

    Neither a generic Ruby project nor a bare ``spec`` directory proves that
    ``bundle exec rspec`` is appropriate. Do not follow linked spec directories
    or marker files during discovery. The CLI still requires ``--yes`` before
    running the discovered command.
    """
    if not names.intersection({'Gemfile', 'gems.rb'}):
        return None
    specs = root / 'spec'
    if specs.is_symlink() or not specs.is_dir():
        return None
    # Rails projects can use rails_helper.rb without spec_helper.rb.
    markers = (root / '.rspec', specs / 'spec_helper.rb', specs / 'rails_helper.rb')
    if not any(marker.is_file() and not marker.is_symlink() for marker in markers):
        return None
    return {
        'ecosystem': 'Ruby',
        'argv': ['bundle', 'exec', 'rspec'],
        'reason': 'Bundler manifest and RSpec configuration',
    }
