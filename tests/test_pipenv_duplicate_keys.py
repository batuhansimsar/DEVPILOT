"""Regression tests for ambiguous Pipenv lockfiles."""

import unittest

from devpilot.pipenv_deps import parse_pipfile_lock


class DuplicateKeyTests(unittest.TestCase):
    def test_duplicate_package_is_rejected_without_leaking_contents(self):
        content = '{"default":{"requests":{"version":"==1"},"requests":{"index":"secret-index"}}}'
        with self.assertRaisesRegex(ValueError, 'duplicate object keys') as caught:
            parse_pipfile_lock(content)
        self.assertNotIn('requests', str(caught.exception))
        self.assertNotIn('secret-index', str(caught.exception))

    def test_duplicate_group_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate object keys'):
            parse_pipfile_lock('{"default":{},"default":{"requests":{}}}')

    def test_duplicate_metadata_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate object keys'):
            parse_pipfile_lock('{"_meta":{"sources":[],"sources":[]}}')

    def test_distinct_group_keys_remain_supported(self):
        self.assertEqual(
            parse_pipfile_lock('{"default":{"my_pkg":{}}, "develop":{"pytest":{}}}'),
            {"default": ["my-pkg"], "develop": ["pytest"]},
        )


if __name__ == '__main__':
    unittest.main()
