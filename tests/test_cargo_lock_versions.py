"""Do not report incomplete Cargo.lock package entries as resolved crates."""

import unittest

from devpilot.cargo_lock import parse_cargo_lock


class CargoLockVersionTests(unittest.TestCase):
    def test_valid_versions_and_duplicate_names(self):
        lock = '''version = 4
[[package]]
name = "serde"
version = "1.0.0"
[[package]]
name = "serde"
version = "1.0.1+build.3"
'''
        self.assertEqual(parse_cargo_lock(lock), ['serde'])

    def test_missing_invalid_and_secret_versions_fail_closed(self):
        versions = ('', 'version = 123\n', 'version = false\n',
                    'version = ""\n', 'version = "  "\n',
                    'version = "1.0\\nsecret"\n')
        for line in versions:
            with self.subTest(line=line):
                source = ('[[package]]\nname = "legitimate"\nversion = "1.0.0"\n'
                          '[[package]]\nname = "phantom"\n' + line +
                          'source = "registry+https://user:secret@example.invalid/index"\n')
                with self.assertRaisesRegex(ValueError, 'version strings') as error:
                    parse_cargo_lock(source)
                self.assertNotIn('secret', str(error.exception))
                self.assertNotIn('example.invalid', str(error.exception))


if __name__ == '__main__':
    unittest.main()
