"""Read-only Go module requirement parsing for dependency inventories."""

from __future__ import annotations

import ast
import re

# Bound direct API calls before allocating a second copy of untrusted input.
# Repository scanners have their own (smaller) manifest read limits.
# Preserve the original character cap and enforce the same budget on UTF-8
# bytes: direct callers may pass multi-byte characters or lone surrogates.
MAX_GO_MOD_INPUT_CHARS = 1_000_000
MAX_GO_MOD_INPUT_BYTES = MAX_GO_MOD_INPUT_CHARS

# Go module path elements accept '+' and '~' in addition to letters, digits,
# dots, underscores and hyphens. Go's modfile syntax is broader than package
# identifiers; excluding these characters drops valid dependencies.
# Paths with just one element (e.g. example.com) are valid too.
# Go also permits double-quoted module paths and versions in require declarations.
_MODULE_PATH = re.compile(r'[A-Za-z0-9_.+~-]+(?:/[A-Za-z0-9_.+~-]+)*\Z')
# File paths reserved by Windows also cannot be Go module path elements.
# Compare the stem before the first dot (CON.txt is reserved too).
_WINDOWS_RESERVED = frozenset({'con', 'prn', 'aux', 'nul'} | {
    f'{kind}{digit}' for kind in ('com', 'lpt') for digit in range(1, 10)
})
_GO_QUOTED_CONTENT = re.compile(
    r'(?:[^"\\]|\\(?:[abfnrtv\\"]|[0-7]{3}|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}))*\Z'
)
_REQUIREMENT = re.compile(
    r'(?:(?P<plain>[A-Za-z0-9_.+~-]+(?:/[A-Za-z0-9_.+~-]+)*)|'
    r'"(?P<quoted>(?:[^"\\]|\\.)*)"|'
    r'`(?P<raw>[^`\r\n]*)`)[ \t]+'
    r'(?:(?P<version_plain>v[^\s"`]+)|'
    r'"(?P<version_quoted>v[^\s"`]+)"|'
    r'`(?P<version_raw>v[^\s"`]+)`)\Z'
)


def _without_go_comments(content: str) -> str:
    """Mask Go line and block comments without changing line boundaries.

    A comment is whitespace to the Go lexer, not arbitrary string removal:
    preserving line breaks prevents a declaration after a multiline comment
    from joining an incomplete requirement on the preceding line. Quoted and
    raw Go strings retain literal comment delimiters. Unclosed block comments or string literals invalidate the file, so fail
    closed rather than reporting a partial scan.
    """
    output: list[str] = []
    index = 0
    quote = ''
    escaped = False
    while index < len(content):
        character = content[index]
        if quote:
            # Go's go.mod quoted and raw string tokens cannot span lines.
            # Failing closed prevents later require lines in an invalid file
            # from appearing as a trustworthy dependency inventory.
            if character in '\r\n':
                raise ValueError('go.mod contains unterminated string literal')
            output.append(character)
            if quote == '"' and escaped:
                escaped = False
            elif quote == '"' and character == '\\':
                escaped = True
            elif character == quote:
                quote = ''
            index += 1
            continue
        if character in ('"', '`'):
            quote = character
            output.append(character)
            index += 1
            continue
        if content.startswith('//', index):
            # A comment ends at a *physical* CR or LF boundary. A CR-only
            # go.mod must not hide the following declaration.
            end = index + 2
            while end < len(content) and content[end] not in '\r\n':
                end += 1
            output.append(' ' * (end - index))
            index = end
            continue
        if content.startswith('/*', index):
            end = content.find('*/', index + 2)
            if end == -1:
                # Treat an incomplete manifest as invalid instead of silently
                # reporting that it has no dependencies. Do not echo source.
                raise ValueError('go.mod contains unterminated block comment')
            comment = content[index:end + 2]
            output.append(''.join(char if char in '\r\n' else ' ' for char in comment))
            index = end + 2
            continue
        output.append(character)
        index += 1
    if quote:
        raise ValueError('go.mod contains unterminated string literal')
    return ''.join(output)


def _valid_module_path(path: str) -> bool:
    """Reject unsafe Go path elements, including Windows device names.

    Go module paths cannot contain reserved Windows filenames or DOS 8.3
    short-name-looking segments. Check the stem before the first dot, as
    Windows also reserves names such as ``CON.txt``.
    """
    if not _MODULE_PATH.fullmatch(path):
        return False
    for element in path.split('/'):
        if element.startswith('.') or element.endswith('.'):
            return False
        stem = element.split('.', 1)[0]
        if stem.lower() in _WINDOWS_RESERVED:
            return False
        # Windows can interpret a trailing '~<digits>' as an 8.3 alias.
        if '~' in stem and stem.rsplit('~', 1)[1].isdigit():
            return False
    return True


def parse_go_requirements(content: str) -> list[str]:
    """Collect dependencies in single-line and parenthesized require blocks.

    Go permits whitespace, double-quoted strings with Go-style escapes, and
    backtick-delimited raw strings.
    Go line and block comments are ignored, including multiline comments.
    Only require declarations are included: replace and exclude do not describe
    additional dependencies. Returned data contains names, no versions.
    """
    if not isinstance(content, str) or len(content) > MAX_GO_MOD_INPUT_CHARS:
        raise ValueError('go.mod input is invalid or exceeds safe size limit')
    try:
        if len(content.encode('utf-8')) > MAX_GO_MOD_INPUT_BYTES:
            raise ValueError('go.mod input is invalid or exceeds safe size limit')
    except UnicodeEncodeError:
        raise ValueError('go.mod input is invalid or exceeds safe size limit') from None
    names: set[str] = set()
    in_require_block = False
    # Reject truncated comments instead of silently reporting an empty inventory.
    # splitlines() treats Unicode separators (NEL, LS, PS, etc.) as real
    # newlines, inventing requirements inside malformed go.mod source.
    # Only CR and LF delimit physical lines.
    physical_lines = _without_go_comments(content.removeprefix('\ufeff'))
    for raw in physical_lines.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        # Go directives tokenize only ASCII spaces/tabs; Python's generic
        # strip/split accept Unicode separators Go rejects.
        line = raw.strip(' \t')
        if not line:
            continue
        if in_require_block:
            if line == ')':
                in_require_block = False
                continue
            # A nested require block is invalid Go syntax. Otherwise its
            # closing ')' prematurely ends the outer block and silently
            # produces a misleading, partial dependency inventory.
            fields = line.split(None, 1)
            if (line == 'require(' or
                    (fields[0] == 'require' and len(fields) == 2
                     and fields[1].lstrip().startswith('('))):
                raise ValueError('go.mod contains nested require block')
            entry = line
        else:
            # Go's modfile syntax also accepts `require(` without a space.
            # This is a block opener, not a single-line requirement.
            if line == 'require(':
                in_require_block = True
                continue
            fields = re.split(r'[ \t]+', line, maxsplit=1)
            if len(fields) != 2 or fields[0] != 'require':
                continue
            entry = fields[1].strip(' \t')
            if entry == '(':
                in_require_block = True
                continue
        match = _REQUIREMENT.fullmatch(entry)
        if match:
            module = match.group('plain')
            if module is None:
                module = match.group('raw')
            if module is None:
                quoted = match.group('quoted')
                if not _GO_QUOTED_CONTENT.fullmatch(quoted):
                    continue
                try:
                    # Decode only string literals; never evaluate expressions.
                    module = ast.literal_eval('"' + quoted + '"')
                except (SyntaxError, ValueError, UnicodeError):
                    continue
            if _valid_module_path(module):
                names.add(module)
    if in_require_block:
        # An incomplete go.mod cannot provide a trustworthy dependency list.
        raise ValueError('go.mod contains unterminated require block')
    return sorted(names)
