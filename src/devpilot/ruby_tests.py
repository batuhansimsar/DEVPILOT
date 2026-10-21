"""Read-only discovery of RSpec and conventional Ruby test commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any


# Use a fixed Ruby expression rather than interpolating untrusted filenames.
# Abort rather than falsely reporting a successful run if no tests are found.
_MINITEST_LOADER = (
    'files = Dir.glob("test/**/*_test.rb").sort; '
    'abort("No Ruby test files found") if files.empty?; '
    'files.each { |file| require File.expand_path(file) }'
)


def ruby_test_command(root: Path, names: set[str]) -> dict[str, Any] | None:
    """Discover RSpec or conventional Ruby tests only in Bundler projects.

    Never execute project code during discovery or follow linked test markers.
    The CLI requires explicit --yes consent before executing any command.
    """
    if not names.intersection({'Gemfile', 'gems.rb'}):
        return None
    specs = root / 'spec'
    if not specs.is_symlink() and specs.is_dir():
        # Rails projects can use rails_helper.rb without spec_helper.rb.
        markers = (root / '.rspec', specs / 'spec_helper.rb', specs / 'rails_helper.rb')
        if any(marker.is_file() and not marker.is_symlink() for marker in markers):
            return {
                'ecosystem': 'Ruby',
                'argv': ['bundle', 'exec', 'rspec'],
                'reason': 'Bundler manifest and RSpec configuration',
            }

    tests = root / 'test'
    helper = tests / 'test_helper.rb'
    if (tests.is_symlink() or not tests.is_dir()
            or helper.is_symlink() or not helper.is_file()):
        return None
    return {
        'ecosystem': 'Ruby',
        'argv': ['bundle', 'exec', 'ruby', '-Itest', '-e', _MINITEST_LOADER],
        'reason': 'Bundler manifest and Ruby test helper',
    }
