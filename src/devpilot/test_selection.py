"""Selection of discovered test commands for polyglot workspaces."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

# Stable, case-independent CLI choices, separate from user-facing ecosystem labels.
ECOSYSTEMS = {
    'node': 'Node.js',
    'deno': 'Deno',
    'dart': 'Dart',
    'python': 'Python',
    'julia': 'Julia',
    'r': 'R',
    'php': 'PHP',
    'cpp': 'C/C++',
    'ruby': 'Ruby',
    'go': 'Go',
    'rust': 'Rust',
    'dotnet': '.NET',
    'java': 'Java',
    'scala': 'Scala',
    'clojure': 'Clojure',
    'haskell': 'Haskell',
    'swift': 'Swift',
    'elixir': 'Elixir',
    'zig': 'Zig',
}


# Common display names and synonyms map to canonical keys, so CLI and
# programmatic selection share the same ecosystem policy.
ECOSYSTEM_ALIASES = {
    'node.js': 'node',
    'nodejs': 'node',
    'js': 'node',
    'javascript': 'node',
    'ts': 'node',
    'typescript': 'node',
    'py': 'python',
    'golang': 'go',
    '.net': 'dotnet',
    'c#': 'dotnet',
    'csharp': 'dotnet',
    'f#': 'dotnet',
    'fsharp': 'dotnet',
    'vb': 'dotnet',
    'visualbasic': 'dotnet',
    'c': 'cpp',
    'c++': 'cpp',
    'c/c++': 'cpp',
    'cxx': 'cpp',
}


def select_test_commands(commands: list[dict[str, Any]], ecosystem: str | None) -> list[dict[str, Any]]:
    """Select commands without sharing mutable state with discovery results.

    Execution annotates selected commands with results and skip reasons.  Deep
    copies also isolate argument lists and any nested discovery metadata so a
    later run cannot silently change the original plan.
    """
    if ecosystem is None:
        return deepcopy(commands)
    # Do not leak unexpected selector values in errors: direct API callers
    # could inadvertently pass private strings or objects here.
    if not isinstance(ecosystem, str):
        raise KeyError('unknown test ecosystem') from None
    try:
        key = ecosystem.casefold()
        label = ECOSYSTEMS[ECOSYSTEM_ALIASES.get(key, key)]
    except KeyError:
        raise KeyError('unknown test ecosystem') from None
    return [deepcopy(command) for command in commands if command['ecosystem'] == label]
