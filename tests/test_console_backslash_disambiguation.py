"""Escaped terminal data must distinguish literal backslashes from controls."""

import unittest

from devpilot.console import escape_terminal


class ConsoleBackslashDisambiguationTests(unittest.TestCase):
    def test_literal_escape_spelling_is_not_an_actual_control(self):
        self.assertEqual(escape_terminal('alert\x1b[31m'), r'alert\x1b[31m')
        self.assertEqual(escape_terminal(r'alert\x1b[31m'), r'alert\\x1b[31m')
        self.assertNotEqual(escape_terminal('alert\x1b[31m'), escape_terminal(r'alert\x1b[31m'))

    def test_unicode_escape_spelling_is_not_an_actual_bidi_mark(self):
        self.assertEqual(escape_terminal('file\u202e.txt'), r'file\u202e.txt')
        self.assertEqual(escape_terminal(r'file\u202e.txt'), r'file\\u202e.txt')

    def test_windows_style_paths_keep_separators_unambiguous(self):
        self.assertEqual(escape_terminal('C:\\Users\\café.txt'), r'C:\\Users\\café.txt')
        self.assertEqual(escape_terminal('café/şifre.pem'), 'café/şifre.pem')


if __name__ == '__main__':
    unittest.main()
