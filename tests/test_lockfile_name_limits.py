"""Bounds for Python lockfile package names and privacy-safe failures."""

import json
import unittest

from devpilot.pipenv_deps import parse_pipfile_lock
from devpilot.uv_lock import parse_uv_lock


class LockfilePackageNameLimitsTests(unittest.TestCase):
    def test_uv_lock_accepts_maximum_length_name(self):
        name = 'a' * 214
        self.assertEqual(parse_uv_lock('[[package]]\nname = "' + name + '"\n'), [name])

    def test_uv_lock_rejects_oversized_name_without_echoing_it(self):
        name = 'secret' + 'x' * 209
        with self.assertRaises(ValueError) as error:
            parse_uv_lock('[[package]]\nname = "' + name + '"\n')
        self.assertNotIn('secret', str(error.exception))

    def test_pipfile_lock_accepts_maximum_length_name(self):
        name = 'a' * 214
        self.assertEqual(parse_pipfile_lock(json.dumps({'default': {name: {}}})),
                         {'default': [name]})

    def test_pipfile_lock_rejects_oversized_names_in_both_groups(self):
        name = 'secret' + 'x' * 209
        for group in ('default', 'develop'):
            with self.subTest(group=group), self.assertRaises(ValueError) as error:
                parse_pipfile_lock(json.dumps({group: {name: {}}}))
            self.assertNotIn('secret', str(error.exception))


if __name__ == '__main__':
    unittest.main()
