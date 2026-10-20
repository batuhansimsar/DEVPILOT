"""Duplicate Pipenv lockfile keys must never silently overwrite dependencies."""

import unittest

from devpilot.pipenv_deps import parse_pipfile_lock


class PipenvStrictJSONTests(unittest.TestCase):
    def test_duplicate_groups_are_rejected(self):
        source = ('{"default":{"first":{}},'
                  '"default":{"second":{}}}')
        with self.assertRaisesRegex(ValueError, "duplicate object keys"):
            parse_pipfile_lock(source)

    def test_duplicate_package_names_are_rejected(self):
        source = '{"default":{"requests":{},"requests":{}}}'
        with self.assertRaisesRegex(ValueError, "duplicate object keys"):
            parse_pipfile_lock(source)

    def test_escaped_duplicate_names_are_rejected(self):
        source = '{"default":{"requests":{},"reques\\u0074s":{}}}'
        with self.assertRaisesRegex(ValueError, "duplicate object keys"):
            parse_pipfile_lock(source)

    def test_nested_metadata_duplicates_do_not_leak_credentials(self):
        source = ('{"_meta":{"sources":[{"url":"https://user:secret@example.test",'
                  '"url":"https://user:another-secret@example.test"}]}}')
        with self.assertRaises(ValueError) as captured:
            parse_pipfile_lock(source)
        self.assertIn("duplicate object keys", str(captured.exception))
        self.assertNotIn("secret", str(captured.exception))
        self.assertNotIn("https", str(captured.exception))
        self.assertNotIn("url", str(captured.exception))

    def test_same_package_in_distinct_groups_is_valid(self):
        source = '{"default":{"requests":{}}, "develop":{"requests":{}}}'
        self.assertEqual(parse_pipfile_lock(source),
                         {"default": ["requests"], "develop": ["requests"]})


if __name__ == "__main__":
    unittest.main()
