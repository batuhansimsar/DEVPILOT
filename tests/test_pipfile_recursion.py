"""Untrusted, deeply nested Pipfile TOML must not crash dependency scans."""

import unittest
from unittest.mock import patch

from devpilot.pipfile_deps import parse_pipfile_dependencies


class PipfileRecursionTests(unittest.TestCase):
    def test_parser_recursion_is_reported_without_disclosing_content(self):
        with patch('devpilot.pipfile_deps.tomllib.loads', side_effect=RecursionError('private')):
            with self.assertRaisesRegex(ValueError, '^invalid Pipfile TOML$') as error:
                parse_pipfile_dependencies('[packages]\nsecret = "private"')
        self.assertNotIn('private', str(error.exception))

    def test_deeply_nested_array_is_a_safe_validation_error(self):
        content = '[packages]\nsecret = ' + '[' * 1200 + '"private"' + ']' * 1200
        with self.assertRaises(ValueError) as error:
            parse_pipfile_dependencies(content)
        self.assertNotIn('secret', str(error.exception))
        self.assertNotIn('private', str(error.exception))


if __name__ == '__main__':
    unittest.main()
