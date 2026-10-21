"""Read-only discovery of RSpec and conventional Ruby test commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any


# Use a fixed Ruby expression rather than interpolating untrusted filenames.
# Abort rather than falsely reporting a successful run if no tests are found.
_MINITEST_LOADER = (
    'abort("No Ruby test files found") if File.symlink?("test"); '
    'files = Dir.glob("test/**/*_test.rb").select { |file| File.file?(file) && !File.symlink?(file) }.sort; '
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
        # Standalone RSpec suites can omit the usual helper file.
        markers = (root / '.rspec', root / '.rspec-local',
                   specs / 'spec_helper.rb', specs / 'rails_helper.rb')
        found_rspec = any(marker.is_file() and not marker.is_symlink() for marker in markers)
        if not found_rspec:
            # Do not recurse into linked directories or trust linked spec files.
            found_rspec = any(
                candidate.is_file() and not candidate.is_symlink()
                for candidate in specs.glob('*_spec.rb')
            )
        if found_rspec:
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
    # A test helper alone is not a runnable suite. Keep the dry-run plan
    # accurate rather than suggesting a command that would only abort.
    try:
        if not any(path.is_file() and not path.is_symlink()
                   for path in tests.rglob('*_test.rb')):
            return None
    except OSError:
        return None
    return {
        'ecosystem': 'Ruby',
        'argv': ['bundle', 'exec', 'ruby', '-Itest', '-e', _MINITEST_LOADER],
        'reason': 'Bundler manifest and Ruby test helper',
    }
