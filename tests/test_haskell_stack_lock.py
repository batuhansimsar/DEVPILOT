"""Regression tests for Stack's lockfile project marker."""

import unittest

from devpilot.haskell_manifests import is_haskell_manifest


class HaskellLockRegression(unittest.TestCase):
    def test_stack_lock_is_manifest(self):
        self.assertTrue(is_haskell_manifest('stack.yaml.lock'))

    def test_unrelated_locks_and_backups_rejected(self):
        for name in (
            'stack.yaml.lock.bak', 'stack.yaml.lock~', 'otherstack.yaml.lock',
            'Stack.yaml.lock', 'stack.yaml.lock/child', 'stack.yaml.lock.old',
            None, 3,
        ):
            with self.subTest(name=name):
                self.assertFalse(is_haskell_manifest(name))


if __name__ == '__main__':
    unittest.main()
