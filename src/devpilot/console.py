"""Safe rendering of untrusted filesystem names in human-readable terminal output."""

from __future__ import annotations


def escape_terminal(value: str) -> str:
    """Show control and formatting codepoints literally, preserving normal Unicode.

    Raw Git filenames may contain newlines, ANSI escapes or bidirectional
    controls. Keeping these escaped prevents spoofed audit lines or log output.
    Machine-readable JSON should retain the original value instead.
    """
    parts: list[str] = []
    for char in value:
        if char == '\\':
            parts.append('\\\\')
        elif char.isprintable():
            parts.append(char)
        else:
            codepoint = ord(char)
            if codepoint <= 0xFF:
                parts.append(f'\\x{codepoint:02x}')
            elif codepoint <= 0xFFFF:
                parts.append(f'\\u{codepoint:04x}')
            else:
                parts.append(f'\\U{codepoint:08x}')
    return ''.join(parts)
