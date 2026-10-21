"""Consistent .NET project and solution marker recognition."""

from __future__ import annotations

from pathlib import Path

DOTNET_PROJECT_SUFFIXES = frozenset({'.csproj', '.fsproj', '.vbproj'})
DOTNET_SOLUTION_SUFFIXES = frozenset({'.sln', '.slnx'})
DOTNET_FILTER_SUFFIXES = frozenset({'.slnf'})
DOTNET_SUFFIXES = DOTNET_PROJECT_SUFFIXES | DOTNET_SOLUTION_SUFFIXES | DOTNET_FILTER_SUFFIXES
DOTNET_ROOT_MARKERS = frozenset({'global.json', 'Directory.Packages.props',
                                 'Directory.Build.props', 'Directory.Build.targets'})


def is_dotnet_manifest(name: str) -> bool:
    """Recognize SDK markers, projects, solutions and solution filters."""
    return isinstance(name, str) and (
        name in DOTNET_ROOT_MARKERS or Path(name).suffix.lower() in DOTNET_SUFFIXES
    )


def dotnet_test_target(names: set[str]) -> str | None:
    """Prefer a unique full solution, then a filter, then a project.

    A full solution takes precedence over its supplementary filters so adding
    an .slnf alongside an existing .sln does not make test discovery ambiguous.
    Multiple targets at the same priority are ambiguous and never guessed.
    """
    for suffixes in (DOTNET_SOLUTION_SUFFIXES, DOTNET_FILTER_SUFFIXES, DOTNET_PROJECT_SUFFIXES):
        candidates = sorted(name for name in names if Path(name).suffix.lower() in suffixes)
        if candidates:
            return candidates[0] if len(candidates) == 1 else None
    return None
