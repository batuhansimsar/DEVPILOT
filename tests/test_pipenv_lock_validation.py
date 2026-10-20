"""Guard against partial or ambiguous Pipfile.lock dependency inventories."""

import json
import unittest

from devpilot.pipenv_deps import parse_pipfile_lock


class PipenvLockValidationTests(unittest.TestCase):
    def test_valid_groups_canonicalize_independently(self):
        content = json.dumps({
            "default": {"Requests": {}, "my_pkg": {}},
            "develop": {"requests": {}, "Py.Test": {}},
        })
        self.assertEqual(parse_pipfile_lock(content), {
            "default": ["my-pkg", "requests"],
            "develop": ["py-test", "requests"],
        })

    def test_invalid_names_fail_closed_without_leaking_content(self):
        for group in ("default", "develop"):
            for name in ("!bad", "bad/name", "bad\x1b[31m", " ", "bad\nname"):
                with self.subTest(group=group, name=name):
                    content = json.dumps({group: {name: {"index": "https://user:secret@example.test"}}})
                    with self.assertRaisesRegex(ValueError, "invalid package name") as caught:
                        parse_pipfile_lock(content)
                    message = str(caught.exception)
                    if name.strip():
                        self.assertNotIn(name, message)
                    self.assertNotIn("secret", message)
                    self.assertNotIn("example.test", message)

    def test_colliding_normalized_names_fail_closed(self):
        for group in ("default", "develop"):
            for pair in (("My_Pkg", "my.pkg"), ("Requests", "requests"), ("a--b", "a_b")):
                with self.subTest(group=group, names=pair):
                    content = json.dumps({group: {pair[0]: {}, pair[1]: {}}})
                    with self.assertRaisesRegex(ValueError, "duplicate normalized package names"):
                        parse_pipfile_lock(content)

    def test_noncolliding_names_remain_sorted(self):
        self.assertEqual(parse_pipfile_lock('{"default":{"z":{"version":"1"},"A":{"version":"2"}}}'),
                         {"default": ["a", "z"]})


if __name__ == "__main__":
    unittest.main()
