"""Go module inventories must honor physical (CR/LF) line boundaries only."""

import unittest

from devpilot.go_mod import parse_go_requirements


class GoModPhysicalLineTests(unittest.TestCase):
    def test_unicode_line_separators_cannot_forge_requirements(self):
        # str.splitlines() treats these Unicode characters as newlines,
        # but none of them terminates a Go source line.
        for separator in ('\x85', '\u2028', '\u2029', '\x0b', '\x0c', '\x1c', '\x1d', '\x1e'):
            with self.subTest(separator=repr(separator)):
                content = 'module example.org/demo' + separator + 'require example.org/forged v1.0.0\n'
                self.assertEqual(parse_go_requirements(content), [])

    def test_cr_only_line_comments_do_not_hide_requirements(self):
        content = (
            'module example.org/demo\r'
            '// ignored comment\r'
            'require example.org/real v1.2.3\r'
        )
        self.assertEqual(parse_go_requirements(content), ['example.org/real'])

    def test_lf_and_crlf_requirements_remain_supported(self):
        content = (
            'module example.org/demo\r\n'
            '// ignored\u2028require example.org/forged v1.0.0\r\n'
            'require example.org/one v1.0.0\n'
            'require example.org/two v2.0.0\r\n'
        )
        self.assertEqual(parse_go_requirements(content), [
            'example.org/one', 'example.org/two',
        ])


if __name__ == '__main__':
    unittest.main()
