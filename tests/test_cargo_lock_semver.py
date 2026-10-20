"""Resolved Cargo.lock versions must be valid SemVer without leaking metadata."""
import unittest

from devpilot.cargo_lock import parse_cargo_lock


class CargoLockSemverTests(unittest.TestCase):
    def test_valid_cargo_semver_and_pre_release(self):
        versions = ('0.0.0', '1.2.3', '999.0.1-alpha.0',
                    '2.1.0-rc.1+build.003', '1.0.0+sha.001')
        for version in versions:
            with self.subTest(version=version):
                source = f'[[package]]\nname = "serde"\nversion = "{version}"\n'
                self.assertEqual(parse_cargo_lock(source), ['serde'])

    def test_rejects_unresolved_non_semver_versions_without_leaking(self):
        invalid = ('latest', '^1.2.3', '1', '1.2', 'v1.2.3',
                   '01.2.3', '1.02.3', '1.2.003', '1.0.0-alpha.01',
                   '1.0.0-', '1.0.0+', '1.0.0-alpha..2', '1.0.0+build..2',
                   '1.0.0/secret', '1.0.0' + 'z' * 300)
        for version in invalid:
            with self.subTest(version=version[:40]):
                source = ('[[package]]\nname = "serde"\nversion = "' + version + '"\n'
                          'source = "registry+https://token:private@example.invalid"\n')
                with self.assertRaisesRegex(ValueError, 'valid version strings') as exc:
                    parse_cargo_lock(source)
                self.assertNotIn('private', str(exc.exception))
                self.assertNotIn(version, str(exc.exception))


if __name__ == '__main__':
    unittest.main()
