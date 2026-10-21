"""Fail closed on unbounded or non-text Go module inputs."""

import unittest

from devpilot.go_mod import MAX_GO_MOD_INPUT_CHARS, parse_go_requirements


class GoModInputBoundsTests(unittest.TestCase):
    def test_rejects_oversized_input_without_leaking_content(self):
        source = 'require example.org/private v1.0.0\n' + ('x' * MAX_GO_MOD_INPUT_CHARS)
        with self.assertRaisesRegex(ValueError, '^go.mod input is invalid or exceeds safe size limit$') as result:
            parse_go_requirements(source)
        self.assertNotIn('private', str(result.exception))

    def test_rejects_non_string_values(self):
        for value in (None, b'require example.org/unsafe v1.0.0', 42, ['require example.org/unsafe v1.0.0']):
            with self.subTest(kind=type(value).__name__):
                with self.assertRaisesRegex(ValueError, 'invalid or exceeds safe size limit'):
                    parse_go_requirements(value)

    def test_valid_input_at_limit_and_normal_requirements(self):
        line = 'require example.org/valid v1.2.3\n'
        content = line + (' ' * (MAX_GO_MOD_INPUT_CHARS - len(line)))
        self.assertEqual(parse_go_requirements(content), ['example.org/valid'])
        self.assertEqual(parse_go_requirements('require example.com/ok v1.0.0\n'), ['example.com/ok'])
