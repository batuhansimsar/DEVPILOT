"""Privacy-safe name inventory for pip requirements files.

Never return repository URLs, version pins, index settings or hash values.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from urllib.parse import parse_qsl

from .pyproject_deps import _EXTRAS, _NAME, _REQUIREMENT, _canonical, _valid_requirement_suffix

# Scanner paths are limited to 512 KB; also bound direct API calls.
MAX_REQUIREMENTS_INPUT_CHARS = 1_000_000

# pip accepts both --hash=algorithm:digest and --hash algorithm:digest.
# Strip one or more options before validating the PEP 508 declaration, while
# keeping all hash material out of the dependency inventory.
_HASH_OPTIONS = re.compile(r'(?:\s+--hash(?:=|\s+)(?:sha256|sha384|sha512):[0-9a-fA-F]+)+\s*\Z')


_EDITABLE_OPTION = re.compile(r'^(?:-e|--editable)(?:\s+|=)(.+)\Z')
_LEGACY_VCS_URL = re.compile(
    r'(?:git|hg|svn|bzr)\+(?:https?|ssh|git|file)://[^\s#]+#([^\s#]+)\Z'
)


def _legacy_vcs_egg_name(target: str) -> str | None:
    """Read only an explicit, valid #egg= name from a legacy pip VCS URL.

    pip accepts this deprecated form in editable and ordinary requirements.
    Ignore all other URL components; they may contain credentials or tokens.
    Reject ambiguous/duplicate fragments rather than selecting one name.
    """
    match = _LEGACY_VCS_URL.fullmatch(target)
    if match is None:
        return None
    try:
        fields = parse_qsl(match.group(1), keep_blank_values=True,
                           strict_parsing=True, max_num_fields=16)
    except ValueError:
        return None
    eggs = [value for key, value in fields if key == 'egg']
    if len(eggs) != 1 or len(eggs[0]) > 512:
        return None
    egg = eggs[0]
    # Legacy pip fragments may append PEP 508 extras to a package name.
    # Validate the complete suffix and return only the canonical base name,
    # never any potentially credential-bearing URL or fragment contents.
    name, bracket, rest = egg.partition('[')
    if bracket and _EXTRAS.fullmatch('[' + rest) is None:
        return None
    if len(name) > 214 or _NAME.fullmatch(name) is None:
        return None
    return _canonical(name)


def _logical_lines(content: str) -> Iterator[str]:
    """Join pip's unescaped backslash continuations before parsing entries.

    A dangling continuation is incomplete and must not create an inventory
    entry. Accumulate fragments in a list so long, bounded files remain cheap.
    A single UTF-8 BOM at the beginning of the document is permitted.
    Only CR, LF, and CRLF delimit physical lines: str.splitlines() also
    splits at Unicode separators and can invent dependencies inside comments.
    """
    fragments: list[str] = []
    for raw in content.removeprefix('\ufeff').replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        line = raw.strip()
        if not line and fragments:
            continue
        # Pip removes the final backslash and newline without inserting a
        # space. Preserve surrounding whitespace so split names, versions and
        # URL paths are not accidentally changed. A backslash followed by
        # spaces is not a continuation.
        trailing = len(raw) - len(raw.rstrip('\\'))
        if trailing % 2:
            fragments.append(raw[:-1])
            continue
        if fragments:
            fragments.append(raw)
            line = ''.join(fragments).strip()
            fragments.clear()
        yield line


def parse_requirements_dependencies(content: str) -> list[str]:
    """Return canonical names from valid requirement declarations only.

    Ignore pip directives, bare anonymous URLs and malformed requirements.
    Include named PEP 508 direct references and legacy VCS #egg references,
    without ever exposing their potentially credential-bearing URLs.
    Join pip-style continuations before parsing declarations; incomplete
    trailing entries are ignored.
    """
    if not isinstance(content, str) or len(content) > MAX_REQUIREMENTS_INPUT_CHARS:
        raise ValueError('requirements input is invalid or exceeds safe size limit')
    # A short sequence of Unicode characters may be much larger in UTF-8.
    # Apply the same byte budget to direct callers, without echoing their data.
    try:
        if len(content.encode('utf-8')) > MAX_REQUIREMENTS_INPUT_CHARS:
            raise ValueError('requirements input is invalid or exceeds safe size limit')
    except UnicodeEncodeError:
        raise ValueError('requirements input must contain valid Unicode') from None
    names: set[str] = set()
    for line in _logical_lines(content):
        if not line or line.startswith(('#', 'https:', 'http:')):
            continue
        # A comment must have whitespace before #; URL fragments are data.
        line = re.split(r'\s+#', line, maxsplit=1)[0].rstrip()
        editable = _EDITABLE_OPTION.fullmatch(line)
        if editable:
            target = editable.group(1).strip()
            if len(target) >= 2 and target[0] in ('"', "'") and target[-1] == target[0]:
                target = target[1:-1]
            legacy_name = _legacy_vcs_egg_name(target)
            if legacy_name is not None:
                names.add(legacy_name)
                continue
            # Editable paths and anonymous VCS refs carry no reliable name.
            # Require an explicit PEP 508 direct-reference name instead.
            match = _REQUIREMENT.match(target)
            if match:
                suffix = target[match.end():].strip()
                if suffix.startswith('['):
                    extras = _EXTRAS.match(suffix)
                    if extras:
                        suffix = suffix[extras.end():].strip()
                if suffix.startswith('@') and _valid_requirement_suffix(target[match.end():]):
                    names.add(_canonical(match.group(1)))
            continue
        if line.startswith(('git+', 'hg+', 'svn+', 'bzr+')):
            legacy_name = _legacy_vcs_egg_name(line)
            if legacy_name is not None:
                names.add(legacy_name)
            continue
        if line.startswith('-'):
            continue
        line = _HASH_OPTIONS.sub('', line).rstrip()
        match = _REQUIREMENT.match(line)
        if match and _valid_requirement_suffix(line[match.end():]):
            names.add(_canonical(match.group(1)))
    return sorted(names)
