"""Legacy Docker registry auth files are potential leaked credentials."""

import unittest

from devpilot.audit import _potential_secret
from devpilot.secret_audit import classify


class DockerConfigCredentialsTests(unittest.TestCase):
    def test_dockercfg_and_backup_names_detected_by_both_auditors(self):
        for name in (
            '.dockercfg', 'nested/.dockercfg', '.DOCKERCFG',
            '.dockercfg.bak', '.dockercfg.~3~', '.#.dockercfg',
            'home\\.dockercfg.old',
        ):
            with self.subTest(name=name):
                self.assertTrue(_potential_secret(name))
                self.assertEqual(classify(name), 'potential credential file')

    def test_templates_and_unrelated_names_are_not_credential_files(self):
        for name in (
            '.dockercfg.example', 'nested/.dockercfg.template.bak',
            'README.md', 'docker-compose.yml', 'config.json',
        ):
            with self.subTest(name=name):
                self.assertFalse(_potential_secret(name))
                self.assertIsNone(classify(name))


if __name__ == '__main__':
    unittest.main()
