"""Malformed Pipenv package names must not result in incomplete inventories."""

import json
import unittest

from devpilot.pipenv_deps import parse_pipfile_lock


class PipenvInvalidNamesTests(unittest.TestCase):
    def test_invalid_names_fail_closed_in_either_group(self):
        for group in ('default', 'develop'):
            for invalid_name in ('', 'broken name', 'private/name', 'trailing-', '.hidden', 'token\nsecret'):
                with self.subTest(group=group, name=invalid_name):
                    content = json.dumps({group: {'requests': {}, invalid_name: {'index': 'private-token'}}})
                    with self.assertRaisesRegex(ValueError, 'invalid package names') as captured:
                        parse_pipfile_lock(content)
                    if invalid_name:
                        self.assertNotIn(invalid_name, str(captured.exception))
                    self.assertNotIn('private-token', str(captured.exception))

    def test_valid_names_still_canonicalize(self):
        content = json.dumps({'default': {'My_Pkg': {}, 'requests': {}}, 'develop': {'Py.Test': {}}})
        self.assertEqual(parse_pipfile_lock(content), {
            'default': ['my-pkg', 'requests'], 'develop': ['py-test'],
        })


if __name__ == '__main__':
    unittest.main()
