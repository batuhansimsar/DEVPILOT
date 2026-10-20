"""Pyproject parser limits should fail closed for direct callers."""

import unittest
from unittest.mock import patch

from devpilot import pyproject_deps


class PyprojectTomlRecursionTests(unittest.TestCase):
    def test_actual_deeply_nested_toml_is_rejected(self):
        nested = 'metadata = ' + '{child = ' * 1000 + '1' + '}' * 1000
        with self.assertRaisesRegex(ValueError, 'Invalid pyproject.toml TOML') as result:
            pyproject_deps.parse_pyproject_dependencies(
                'source = "https://user:secret@example.invalid"\n' + nested
            )
        self.assertNotIn('secret', str(result.exception))

    def test_recursion_error_does_not_reflect_untrusted_message(self):
        with patch.object(pyproject_deps.tomllib, 'loads',
                          side_effect=RecursionError('token=private')):
            with self.assertRaisesRegex(ValueError, 'Invalid pyproject.toml TOML') as result:
                pyproject_deps.parse_pyproject_dependencies('source="token=private"')
        self.assertTrue(result.exception.__suppress_context__)
        self.assertNotIn('private', str(result.exception))


if __name__ == '__main__':
    unittest.main()
