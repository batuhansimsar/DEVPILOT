"""Direct requirements parser calls have bounded and privacy-safe failures."""

import unittest

from devpilot.requirements_deps import (
    MAX_REQUIREMENTS_INPUT_CHARS,
    parse_requirements_dependencies,
)


class RequirementsInputLimitTests(unittest.TestCase):
    def test_rejects_non_string_input_without_exposing_its_representation(self):
        for content in (None, b'requests==2', ['secret'], {'token': 'private'}):
            with self.subTest(content_type=type(content).__name__):
                with self.assertRaisesRegex(ValueError, 'safe size limit') as raised:
                    parse_requirements_dependencies(content)
                self.assertNotIn('secret', str(raised.exception))
                self.assertNotIn('private', str(raised.exception))

    def test_rejects_oversized_input_before_parsing(self):
        secret = 'token-secret'
        content = ('#' * MAX_REQUIREMENTS_INPUT_CHARS) + secret
        with self.assertRaises(ValueError) as raised:
            parse_requirements_dependencies(content)
        self.assertNotIn(secret, str(raised.exception))

    def test_accepts_limit_and_retains_valid_dependency_names(self):
        content = ('#' * (MAX_REQUIREMENTS_INPUT_CHARS - len('\nrequests==2\n'))) + '\nrequests==2\n'
        self.assertEqual(len(content), MAX_REQUIREMENTS_INPUT_CHARS)
        self.assertEqual(parse_requirements_dependencies(content), ['requests'])
        self.assertEqual(parse_requirements_dependencies('requests==2\nflask >=2\n'),
                         ['flask', 'requests'])


if __name__ == '__main__':
    unittest.main()
