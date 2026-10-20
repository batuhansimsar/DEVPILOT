"""Detect alternate environment filename conventions without flagging templates."""

import unittest

from devpilot.audit import _potential_secret
from devpilot.secret_audit import classify


class NamedEnvironmentFilesTests(unittest.TestCase):
    def test_alternate_environment_names_are_detected(self):
        for name in (
            'production.env', 'services/api/development.env',
            'apps/api/production.env.local', 'PRODUCTION.ENV',
            'production.env.example.local', 'production.env.bak',
        ):
            with self.subTest(name=name):
                self.assertTrue(_potential_secret(name), name)
                self.assertEqual(classify(name), 'environment file')

    def test_named_environment_templates_are_excluded(self):
        for name in (
            'production.env.example', 'production.env.sample',
            'backend/development.env.template', 'PRODUCTION.ENV.DIST',
            'staging.env.defaults', 'production.env.local.sample',
        ):
            with self.subTest(name=name):
                self.assertFalse(_potential_secret(name), name)
                self.assertIsNone(classify(name))

    def test_unrelated_names_remain_unflagged(self):
        for name in ('main.envrc', 'dotenv.txt', 'environment.py', 'env.production'):
            with self.subTest(name=name):
                self.assertFalse(_potential_secret(name), name)
                self.assertIsNone(classify(name))


if __name__ == '__main__':
    unittest.main()
