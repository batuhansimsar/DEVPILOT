"""Regression tests for dependency-looking TOML multiline string contents."""

import unittest

from devpilot.cargo_deps import parse_cargo_dependencies


class CargoTomlStructureTests(unittest.TestCase):
    def test_multiline_strings_cannot_inject_fake_sections(self):
        source = '''
[package]
name = "demo"
description = """
[dependencies]
secret_token = "this is not a package"
[target.'cfg(unix)'.dev-dependencies]
ghost = "not a package"
"""
[dependencies]
serde = "1.0"
'''
        self.assertEqual(parse_cargo_dependencies(source), {'dependencies': ['serde']})

    def test_multiline_dependency_values_do_not_create_packages(self):
        source = '''
[dependencies]
serde = "1"
real = { package = "actual", version = "1" }
fake = """first line
pretend = "1.0"
"""
'''
        self.assertEqual(parse_cargo_dependencies(source), {
            'dependencies': ['fake', 'real', 'serde'],
        })

    def test_multiline_literal_and_inline_delimiter(self):
        source = """
[package]
description = '''[dependencies]
not_real = 'private'
'''
[workspace.dependencies]
real = '1'
"""
        self.assertEqual(parse_cargo_dependencies(source), {'dependencies': ['real']})

    def test_escaped_delimiter_does_not_terminate_multiline_string(self):
        source = r'''
[package]
description = """
\""" not a terminator
[dependencies]
not_a_dep = "token"
"""
[dependencies]
actual = "1"
'''
        self.assertEqual(parse_cargo_dependencies(source), {'dependencies': ['actual']})

    def test_comments_cannot_open_fake_multiline_values(self):
        source = '''
[package]
# The documentation contains """ but is not a TOML string.
[dependencies]
serde = "1"
'''
        self.assertEqual(parse_cargo_dependencies(source), {'dependencies': ['serde']})

    def test_recovers_after_malformed_table(self):
        source = '[dependencies]\nserde = "1"\n[bad] text\nghost = "secret"\n[dev-dependencies]\ncriterion = "1"\n'
        self.assertEqual(parse_cargo_dependencies(source), {
            'dependencies': ['serde'], 'dev-dependencies': ['criterion'],
        })


if __name__ == '__main__':
    unittest.main()
