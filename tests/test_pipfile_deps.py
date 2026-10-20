"""Pipenv Pipfile inventory and credential-privacy regression tests."""

import unittest

from devpilot.pipfile_deps import parse_pipfile_dependencies


class PipfileDependenciesTests(unittest.TestCase):
    def test_versions_inline_tables_and_dev_group(self):
        content = '''[[source]]
url = "https://user:top-secret@private.example/simple"
[packages]
Requests = "^2.31"
My_Pkg = {git = "https://private:secret@host/repo.git", ref = "secret-branch"}
[dev-packages]
PyTest = "*"
'''
        result = parse_pipfile_dependencies(content)
        self.assertEqual(result, {"packages": ["my-pkg", "requests"],
                                  "dev-packages": ["pytest"]})
        self.assertNotIn("secret", str(result))
        self.assertNotIn("private.example", str(result))

    def test_empty_optional_groups_and_bom(self):
        self.assertEqual(parse_pipfile_dependencies("\ufeff[packages]\nFlask = '*'\n"),
                         {"packages": ["flask"]})
        self.assertEqual(parse_pipfile_dependencies("[scripts]\nstart = 'python main.py'"), {})

    def test_duplicate_normalized_names_rejected_without_reflection(self):
        with self.assertRaisesRegex(ValueError, "duplicate normalized") as error:
            parse_pipfile_dependencies('[packages]\nSecret_Pkg = "*"\nsecret-pkg = "1"\n')
        self.assertNotIn("Secret", str(error.exception))

    def test_invalid_specifications_fail_closed(self):
        for spec in ('true', '123', '["abc"]'):
            with self.subTest(spec=spec), self.assertRaisesRegex(ValueError, 'specification'):
                parse_pipfile_dependencies(f'[packages]\nprivate = {spec}\n')

    def test_invalid_names_and_long_names_are_not_echoed(self):
        for name in ('secret@bad', 'secret' + 'x' * 209):
            with self.subTest(name=name), self.assertRaises(ValueError) as error:
                parse_pipfile_dependencies(f'[packages]\n"{name}" = "*"\n')
            self.assertNotIn('secret', str(error.exception))

    def test_malformed_toml_does_not_leak_source_credentials(self):
        with self.assertRaisesRegex(ValueError, 'invalid Pipfile TOML') as error:
            parse_pipfile_dependencies('[source]\nurl = "https://secret@host"\n[packages\n')
        self.assertNotIn('secret', str(error.exception))


if __name__ == '__main__':
    unittest.main()
