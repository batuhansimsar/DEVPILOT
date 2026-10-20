"""Regression tests for tracked cloud-storage client credential filenames."""

import unittest

from devpilot.secret_audit import classify


class StorageClientCredentialsTests(unittest.TestCase):
    def test_storage_client_configs_are_reported(self):
        for path in (
            '.s3cfg', 'home/.s3cfg', 'PROFILE\\.BOTO',
            'config/rclone/rclone.conf', 'RCLONE.CONF',
            'backups/rclone.conf.bak.old', '.s3cfg~', '.boto.swp',
        ):
            with self.subTest(path=path):
                self.assertEqual(classify(path), 'potential credential file')

    def test_templates_and_unrelated_files_are_not_reported(self):
        for path in (
            '.s3cfg.example', '.boto.sample', 'rclone.conf.template',
            'rclone.conf.example.bak', 'rclone.conf.dist',
            'docs/rclone.md', 'config/storage.conf',
        ):
            with self.subTest(path=path):
                self.assertIsNone(classify(path))


if __name__ == '__main__':
    unittest.main()
