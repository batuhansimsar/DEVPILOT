"""Bound direct pyproject parser calls before parsing private manifest contents."""

import unittest
from unittest.mock import patch

from devpilot.pyproject_deps import MAX_PYPROJECT_INPUT_CHARS, parse_pyproject_dependencies


class PyprojectInputLimitTests(unittest.TestCase):
    def test_non_text_inputs_are_rejected_before_toml_parsing(self):
        for value in (None, 12, b'[project]', {'source': 'secret'}):
            with self.subTest(type=type(value).__name__):
                with patch('devpilot.pyproject_deps.tomllib.loads') as parser:
                    with self.assertRaisesRegex(ValueError, 'input is invalid or exceeds safe size limit'):
                        parse_pyproject_dependencies(value)
                    parser.assert_not_called()

    def test_oversized_input_is_rejected_without_parsing_or_echoing_secrets(self):
        secret = 'user:private-token@example.invalid'
        content = '#' * MAX_PYPROJECT_INPUT_CHARS + secret
        with patch('devpilot.pyproject_deps.tomllib.loads') as parser:
            with self.assertRaises(ValueError) as raised:
                parse_pyproject_dependencies(content)
            parser.assert_not_called()
        self.assertNotIn(secret, str(raised.exception))

    def test_multibyte_content_is_rejected_before_toml_parsing(self):
        # Character counts understate the size of UTF-8 TOML documents.
        content = 'note = "' + ('é' * (MAX_PYPROJECT_INPUT_CHARS // 2)) + '"'
        self.assertLess(len(content), MAX_PYPROJECT_INPUT_CHARS)
        with patch('devpilot.pyproject_deps.tomllib.loads') as parser:
            with self.assertRaisesRegex(ValueError, 'safe size limit') as raised:
                parse_pyproject_dependencies(content)
            parser.assert_not_called()
        self.assertNotIn('note', str(raised.exception))

    def test_unencodable_surrogates_are_rejected_without_parsing(self):
        with patch('devpilot.pyproject_deps.tomllib.loads') as parser:
            with self.assertRaisesRegex(ValueError, 'invalid') as raised:
                parse_pyproject_dependencies('secret = "\\ud800"'.replace('\\ud800', chr(0xD800)))
            parser.assert_not_called()
        self.assertIsNone(raised.exception.__cause__)
        self.assertNotIn('secret', str(raised.exception))

    def test_exact_utf8_byte_limit_is_accepted(self):
        content = 'é' * (MAX_PYPROJECT_INPUT_CHARS // 2)
        with patch('devpilot.pyproject_deps.tomllib.loads', return_value={}) as parser:
            self.assertEqual(parse_pyproject_dependencies(content), {})
        parser.assert_called_once_with(content)

    def test_exact_size_limit_is_accepted(self):
        content = '#' * MAX_PYPROJECT_INPUT_CHARS
        with patch('devpilot.pyproject_deps.tomllib.loads', return_value={}) as parser:
            self.assertEqual(parse_pyproject_dependencies(content), {})
        parser.assert_called_once_with(content)

    def test_small_manifest_keeps_dependency_inventory(self):
        self.assertEqual(
            parse_pyproject_dependencies('[project]\ndependencies=["httpx>=0.27"]\n'),
            {'dependencies': ['httpx']},
        )


if __name__ == '__main__':
    unittest.main()
